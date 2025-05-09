# app/db/models/__init__.py
# Import tenant model first since others reference it
from app.db.models.tenant import Tenant

# Then models with no tenant dependencies
from app.db.models.symbol import Symbol
from app.db.models.eod_data import EODData
from app.db.models.feature_data import FeatureData

# Then models with tenant dependencies
from app.db.models.user import User
from app.db.models.tenant_symbol import TenantSymbol
from app.db.models.prediction import Prediction
from app.db.models.config_param import ConfigParam
from app.db.models.prediction_model import PredictionModel
from app.db.models.model_performance import ModelPerformance
