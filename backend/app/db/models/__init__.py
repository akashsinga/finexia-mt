# Import all models here to ensure proper initialization order
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.models.symbol import Symbol
from app.db.models.eod_data import EODData
from app.db.models.prediction import Prediction
from app.db.models.config_param import ConfigParam
from app.db.models.prediction_model import PredictionModel
from app.db.models.model_performance import ModelPerformance
# Include all other model imports