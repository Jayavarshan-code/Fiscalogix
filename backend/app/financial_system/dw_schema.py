# DEPRECATED: All DW models are now defined in setup_db.py under the shared Base.
# This file is kept only as a compatibility shim — do not add new models here.
# Any import of DW classes should be updated to: from setup_db import <ClassName>
from setup_db import (
    DWShipmentFact,
    DWNodeDimension,
    DWInventoryFact,
    DWLaneDimension,
    DWSupplierDimension,
    DWProductDimension,
    DWCustomerDimension,
)

__all__ = [
    "DWShipmentFact",
    "DWNodeDimension",
    "DWInventoryFact",
    "DWLaneDimension",
    "DWSupplierDimension",
    "DWProductDimension",
    "DWCustomerDimension",
]
