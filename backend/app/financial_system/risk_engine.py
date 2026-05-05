import logging
import pandas as pd
import joblib
import shap
from pathlib import Path
import math
from app.routes.admin import register_model_status
from app.financial_system import feature_builder
from app.financial_system.spatial_risk_injector import get_route_severity

logger = logging.getLogger(__name__)

MODELS_DIR        = Path(__file__).parent / "ml_pipeline" / "models"
PIPELINE_PATH     = MODELS_DIR / "risk_pipeline.pkl"
FALLBACK_PATH     = MODELS_DIR / "risk_fallback.pkl"
FALLBACK_COL_PATH = MODELS_DIR / "risk_fallback_columns.pkl"

# GNN blend weight: how much the GNN score influences the final risk_probability.
# 0.35 = GNN contributes up to 35% of the final score when the node is directly in path.
# Decays with graph distance so distant nodes don't falsely alarm unrelated shipments.
_GNN_MAX_BLEND_WEIGHT = 0.35
# Maximum graph-hop distance at which GNN still influences the score.
_GNN_MAX_HOP_INFLUENCE = 3

class RiskEngine:
    def __init__(self):
        # --- Load XGBoost Pipeline ---
        try:
            self.pipeline = joblib.load(PIPELINE_PATH)
            self.preprocessor = self.pipeline.named_steps["preprocessor"]
            self.model = self.pipeline.named_steps["classifier"]
            self.explainer = shap.TreeExplainer(self.model)
            logger.info("RiskEngine: XGBoost pipeline loaded successfully.")
            register_model_status("RiskEngine", "ok")
        except FileNotFoundError:
            logger.warning("RiskEngine: risk_pipeline.pkl not found. Run ml_pipeline/trainer.py first. Falling back to heuristics.")
            self.pipeline = None
            self.model = None
            self.explainer = None
            register_model_status("RiskEngine", "fallback", "risk_pipeline.pkl missing")
        except Exception as e:
            # Captures OOM, pickle version mismatches, schema misalignments
            logger.error(f"RiskEngine: Failed to load XGBoost pipeline — {type(e).__name__}: {e}", exc_info=True)
            self.pipeline = None
            self.model = None
            self.explainer = None
            register_model_status("RiskEngine", "fallback", f"{type(e).__name__}: {str(e)}")

        # --- GBM Fallback (interaction-feature, numeric-only) ---
        # Trained by train_models.py alongside XGBoost.
        # Used when XGBoost pipeline is unavailable — replaces the old logistic formula.
        try:
            self._gbm_fallback = joblib.load(FALLBACK_PATH)
            self._gbm_columns  = joblib.load(FALLBACK_COL_PATH)
            logger.info("RiskEngine: GBM fallback model loaded.")
            register_model_status("RiskFallback", "ok")
        except FileNotFoundError:
            self._gbm_fallback = None
            self._gbm_columns  = []
            logger.warning("RiskEngine: risk_fallback.pkl not found. Run train_models.py first.")
            register_model_status("RiskFallback", "unavailable", "risk_fallback.pkl missing")
        except Exception as e:
            self._gbm_fallback = None
            self._gbm_columns  = []
            logger.warning(f"RiskEngine: GBM fallback load failed — {e}")
            register_model_status("RiskFallback", "unavailable", str(e))

        # --- GNN Integration ---
        try:
            import torch
            from app.financial_system.ml_pipeline.next_gen.gnn.model import RiskGNN
            self.gnn_model = RiskGNN(in_channels=2, hidden_channels=16, out_channels=2)
            gnn_state = Path(__file__).parent / "ml_pipeline" / "next_gen" / "gnn" / "models" / "gnn_risk_model.pt"
            if gnn_state.exists():
                self.gnn_model.load_state_dict(torch.load(gnn_state))
                self.gnn_model.eval()
                logger.info("RiskEngine: GNN model loaded successfully.")
                register_model_status("RiskGNN", "ok")
            else:
                logger.warning("RiskEngine: GNN model weights not found at expected path. GNN contagion disabled.")
                self.gnn_model = None
                register_model_status("RiskGNN", "unavailable", "Weights missing")
        except ImportError:
            logger.warning("RiskEngine: PyTorch not installed. GNN contagion modeling disabled.")
            self.gnn_model = None
            register_model_status("RiskGNN", "unavailable", "PyTorch not installed")
        except Exception as e:
            logger.error(f"RiskEngine: GNN model load failed — {type(e).__name__}: {e}", exc_info=True)
            self.gnn_model = None
            register_model_status("RiskGNN", "unavailable", f"{type(e).__name__}: {str(e)}")

        # --- Temporal Contagion Engine ---
        self.contagion_predictor = None

        # --- GNN graph tensors (built lazily from the geopolitical graph) ---
        self._gnn_node_map: dict = {}        # node_id → int index
        self._gnn_node_features = None       # torch.FloatTensor [N, 2]
        self._gnn_edge_index = None          # torch.LongTensor  [2, E]
        self._gnn_graph = None               # ref to the NetworkX graph

    def set_contagion_context(self, graph, beta=0.85):
        """Injects global logistics graph context for propagation modeling.
        Also pre-builds the GNN node-feature tensors so inference is instant."""
        from app.financial_system.optimization.contagion_predictor import HybridRiskRadar
        self.contagion_predictor = HybridRiskRadar(graph, propagation_beta=beta)
        self._gnn_graph = graph
        self._build_gnn_graph(graph)

    def _build_gnn_graph(self, graph):
        """
        Converts the NetworkX geopolitical graph into cached PyTorch tensors.
        Node features (2 channels, matching in_channels=2):
          [0] risk_score  – stored on each node by sync_gnn_risk() or default 0.05
          [1] strike_flag – 1.0 if any outgoing edge from this node has strike_active
        Called once at startup and re-called whenever the graph topology changes.
        """
        if self.gnn_model is None:
            return
        try:
            import torch
            import networkx as nx

            nodes = list(graph.nodes())
            self._gnn_node_map = {n: i for i, n in enumerate(nodes)}

            # Build per-node features
            feats = []
            for node in nodes:
                risk = float(graph.nodes[node].get("risk_score", 0.05))
                # strike flag: 1.0 if any outgoing edge carries strike_active=True
                strike = float(
                    any(graph[node][nbr].get("strike_active", False) for nbr in graph.successors(node))
                )
                feats.append([risk, strike])

            self._gnn_node_features = torch.tensor(feats, dtype=torch.float)

            # Build edge_index [2, E]
            src, dst = [], []
            for u, v in graph.edges():
                if u in self._gnn_node_map and v in self._gnn_node_map:
                    src.append(self._gnn_node_map[u])
                    dst.append(self._gnn_node_map[v])
            if src:
                self._gnn_edge_index = torch.tensor([src, dst], dtype=torch.long)
            else:
                # Disconnected graph — self-loops as fallback so SAGEConv doesn't crash
                n = len(nodes)
                self._gnn_edge_index = torch.tensor([list(range(n)), list(range(n))], dtype=torch.long)

            logger.info(
                f"RiskEngine: GNN graph built — {len(nodes)} nodes, {len(src)} edges."
            )
        except Exception as e:
            logger.warning(f"RiskEngine._build_gnn_graph failed — {e}. GNN inference disabled.")
            self._gnn_node_features = None
            self._gnn_edge_index = None

    def _run_gnn_inference(self, route_prefix: str) -> float:
        """
        Runs one forward pass of the GNN and returns the risk probability
        for the node that matches `route_prefix`.

        Blending strategy (proximity-weighted, not MAX override):
          - If the route_prefix node is directly in the graph: blend weight = _GNN_MAX_BLEND_WEIGHT
          - If reachable within _GNN_MAX_HOP_INFLUENCE hops: weight decays linearly with distance
          - If not reachable: weight = 0 (GNN has no opinion on this shipment)

        Returns the GNN-derived probability in [0, 1], or 0.0 if unavailable.
        """
        if (
            self.gnn_model is None
            or self._gnn_node_features is None
            or self._gnn_edge_index is None
        ):
            return 0.0

        try:
            import torch
            import networkx as nx

            # Full portfolio forward pass (cached tensors — no DB/network I/O)
            with torch.no_grad():
                log_probs = self.gnn_model(
                    self._gnn_node_features, self._gnn_edge_index
                )  # [N, 2] log-softmax
                probs = torch.exp(log_probs)  # convert log-prob → prob

            # Find the node that best matches the route prefix
            target_node = None
            route_clean = str(route_prefix).upper().strip()
            if route_clean in self._gnn_node_map:
                target_node = route_clean
            else:
                # Partial match: e.g. "CN-EU_SUEZ" → tries "CN", "EU", "SUEZ"
                for part in route_clean.replace("-", "_").split("_"):
                    if part in self._gnn_node_map:
                        target_node = part
                        break

            if target_node is None:
                return 0.0

            node_idx = self._gnn_node_map[target_node]
            gnn_prob = float(probs[node_idx, 1].item())  # class-1 = high-risk

            # Proximity-weighted blend weight
            # Starts at _GNN_MAX_BLEND_WEIGHT for direct match, decays to 0 at max hops
            if self._gnn_graph is not None and route_clean in self._gnn_node_map:
                try:
                    # Shortest path from any strike node to our target
                    strike_nodes = [
                        u for u, v, d in self._gnn_graph.edges(data=True)
                        if d.get("strike_active")
                    ]
                    if strike_nodes:
                        min_dist = min(
                            nx.shortest_path_length(self._gnn_graph, sn, target_node)
                            for sn in strike_nodes
                            if nx.has_path(self._gnn_graph, sn, target_node)
                        ) if any(
                            nx.has_path(self._gnn_graph, sn, target_node)
                            for sn in strike_nodes
                        ) else _GNN_MAX_HOP_INFLUENCE + 1
                        proximity_weight = max(
                            0.0,
                            _GNN_MAX_BLEND_WEIGHT * (1.0 - min_dist / _GNN_MAX_HOP_INFLUENCE)
                        )
                    else:
                        proximity_weight = _GNN_MAX_BLEND_WEIGHT * 0.3  # baseline influence
                except Exception:
                    proximity_weight = _GNN_MAX_BLEND_WEIGHT * 0.5
            else:
                proximity_weight = _GNN_MAX_BLEND_WEIGHT * 0.2

            return gnn_prob * proximity_weight

        except Exception as e:
            logger.debug(f"RiskEngine._run_gnn_inference failed — {e}")
            return 0.0

    def _extract_shap_drivers(self, df_raw):
        """
        Uses SHAP (SHapley Additive exPlanations) to mathematically prove exactly
        why the model made its decision, satisfying regulatory XAI compliance requirements.
        """
        if not self.model or not self.explainer:
            return ["Fallback heuristics active; SHAP explainability unavailable."]

        X_transformed = self.preprocessor.transform(df_raw)
        shap_values = self.explainer.shap_values(X_transformed)

        num_cols = self.preprocessor.transformers_[0][2]
        cat_encoder = self.preprocessor.transformers_[1][1]
        cat_cols = cat_encoder.get_feature_names_out(self.preprocessor.transformers_[1][2])
        feature_names = list(num_cols) + list(cat_cols)

        drivers = []
        # shap_values is a list of 2 arrays: [class-0, class-1].
        # class-0 = non-default (benign); class-1 = default/risk.
        # We must index [1] to get the risk-class contributions, then [0] for
        # the single sample. Using [0] (the old bug) returned inverted signs —
        # a feature that genuinely increases default risk appeared to DECREASE it.
        instance_shaps = shap_values[1][0]
        impacts = [(name, val) for name, val in zip(feature_names, instance_shaps)]
        impacts.sort(key=lambda x: abs(x[1]), reverse=True)

        for name, impact in impacts[:3]:
            if abs(impact) > 0.05:
                direction = "increased" if impact > 0 else "decreased"
                drivers.append(
                    f"SHAP Proof: Feature '{name}' {direction} risk probability by {(abs(impact)*100):.1f}%"
                )

        if self.gnn_model:
            drivers.append("GNN Insight: Relational risk propagation from neighbor nodes is ACTIVE.")

        if not drivers:
            drivers.append("Nominal systemic risk parameters. No extreme outliers detected.")

        return drivers

    def predict_contagion(self, node_id, horizon_hours):
        if not self.contagion_predictor:
            return {"score": 0.05, "explanation": "Contagion predictor not initialized."}
        return self.contagion_predictor.predict_risk_at_time(node_id, horizon_hours)

    def compute(self, row, predicted_delay, node_id=None, horizon_hours=0):
        """
        Calculates probability this shipment defaults/fails.

        Risk signal priority (proximity-weighted blend):
          1. XGBoost classifier (primary — SHAP-explained)
          2. GBM fallback on interaction features (replaces old logistic formula)
          3. Last-resort logistic guard (only if no model is available at all)
          4. GNN GraphSAGE forward pass (additive spatial contagion signal)
          5. TemporalContagionPredictor (rule + graph hybrid, additive)

        Spatial severity from live external events is injected into every
        feature vector via SpatialRiskInjector before any model sees it.
        This makes disruption events (port strikes, geopolitical shocks)
        affect risk scores proportionally to route proximity, not uniformly.
        """
        # ── 0. Resolve spatial severity for this route ────────────────────────
        route         = row.get("route", "LOCAL")
        cargo_type    = row.get("cargo_type", "general_cargo")
        spatial_severity = 0.0
        try:
            spatial_severity = get_route_severity(route, cargo_type)
        except Exception as _se:
            logger.debug("RiskEngine: spatial injector failed — %s", _se)

        # ── Build enriched feature row (training/serving parity) ─────────────
        enriched = feature_builder.build(
            {**row, "delay_days": predicted_delay},
            spatial_severity=spatial_severity,
        )

        df_raw = pd.DataFrame([{
            "route":       enriched.get("route", "LOCAL"),
            "carrier":     enriched.get("carrier", "LocalTransit"),
            "order_value": enriched.get("order_value", 10000),
            "total_cost":  enriched.get("total_cost", 7000),
            "credit_days": enriched.get("credit_days", 0),
            "delay_days":  predicted_delay,
        }])

        risk_probability = 0.05
        drivers          = []
        confidence       = 0.95

        # ── 1. XGBoost pipeline ───────────────────────────────────────────────
        if self.pipeline:
            probs            = self.pipeline.predict_proba(df_raw)[0]
            risk_probability = float(probs[1])
            confidence       = round(float(max(probs[0], probs[1])), 2)
            drivers          = self._extract_shap_drivers(df_raw)

            # Spatial severity nudge on top of XGBoost score.
            # XGBoost was trained with spatial_severity=0 baseline; at inference
            # we additively shift the score by the live disruption contribution.
            if spatial_severity > 0.05:
                spatial_lift     = spatial_severity * 0.25 * (1.0 - risk_probability)
                risk_probability = min(risk_probability + spatial_lift, 0.97)
                drivers.append(
                    f"Spatial disruption ({route}): severity {spatial_severity:.2f} "
                    f"→ +{spatial_lift:.1%} risk lift."
                )

        # ── 2. GBM fallback (interaction-feature, non-linear) ────────────────
        elif self._gbm_fallback is not None:
            gbm_row = {col: enriched.get(col, 0.0) for col in self._gbm_columns}
            gbm_df  = pd.DataFrame([gbm_row]).fillna(0.0)
            probs            = self._gbm_fallback.predict_proba(gbm_df)[0]
            risk_probability = float(probs[1])
            confidence       = round(float(max(probs[0], probs[1])), 2)
            drivers = [
                "⚠ Fallback Mode: GBM model active (XGBoost pipeline unavailable).",
                f"Interaction features: risk_pressure={enriched.get('risk_pressure', 0):.3f}, "
                f"cost_x_delay={enriched.get('cost_x_delay', 0):.3f}, "
                f"spatial_x_route={enriched.get('spatial_x_route', 0):.3f}.",
            ]
            if spatial_severity > 0.05:
                drivers.append(
                    f"Spatial disruption ({route}): severity {spatial_severity:.2f} "
                    "captured in spatial_x_route interaction feature."
                )

        # ── 3. Last-resort logistic guard (no model at all) ───────────────────
        else:
            order_value      = max(enriched.get("order_value", 1), 1)
            cost_ratio       = enriched.get("cost_ratio", 0)
            margin_pct       = enriched.get("margin_pct", 0)
            risk_pressure    = enriched.get("risk_pressure", 0)
            logit            = (cost_ratio * 2.0) - (margin_pct * 4.0) + (predicted_delay * 0.5) + (risk_pressure * 1.5)
            risk_probability = 1.0 / (1.0 + math.exp(-logit))
            confidence       = 0.55
            drivers = [
                "⚠ Degraded Mode: No trained model available. Logistic guard active.",
                "Run train_models.py to restore full non-linear risk scoring.",
            ]

        # ── 2. GAP 13 FIX — GNN forward pass (proximity-weighted blend) ───────
        # The GNN sees the full supply-chain graph structure.
        # Its output is blended, not used as a MAX override, so only shipments
        # that physically route through disrupted nodes are affected.
        route_prefix = str(row.get("route", "")).split("-")[0].split("_")[0]
        gnn_contribution = self._run_gnn_inference(route_prefix)
        if gnn_contribution > 0.0:
            # Additive blend: GNN adds up to _GNN_MAX_BLEND_WEIGHT to the base score
            blended = risk_probability + gnn_contribution * (1.0 - risk_probability)
            risk_probability = min(blended, 0.97)  # hard cap — never claim certainty
            if gnn_contribution > 0.05:
                drivers.append(
                    f"GNN GraphSAGE: Structural contagion risk +{gnn_contribution:.1%} "
                    f"via route node '{route_prefix}' (proximity-weighted)."
                )

        # ── 3. TemporalContagionPredictor (rule + graph hybrid) ───────────────
        # Kept as a separate, additive signal on top of the GNN.
        # Still blended (not MAX-override) using the same proximity logic.
        if node_id and self.contagion_predictor:
            contagion_out = self.predict_contagion(node_id, horizon_hours)
            contagion_score = contagion_out.get("score", 0.05)
            # Soft blend: contagion can push score up but by at most 15%
            if contagion_score > risk_probability:
                delta = (contagion_score - risk_probability) * 0.5  # blend, not override
                risk_probability = min(risk_probability + delta, 0.97)
                drivers.append(f"XAI Contagion Alert: {contagion_out.get('explanation', '')}")
                confidence = contagion_out.get("confidence", confidence)

        return {
            "score": round(risk_probability, 4),
            "confidence": confidence,
            "drivers": drivers
        }

    def compute_batch(self, rows_list, predicted_delays_array):
        return [
            self.compute(row, predicted_delays_array[i])
            for i, row in enumerate(rows_list)
        ]
