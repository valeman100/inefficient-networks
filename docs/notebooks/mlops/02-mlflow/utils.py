import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import joblib

from toolz import compose
from pathlib import Path
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import make_pipeline
from sklearn.base import BaseEstimator, TransformerMixin

from pandas.core.common import SettingWithCopyWarning
import warnings
warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)

from matplotlib_inline import backend_inline
backend_inline.set_matplotlib_formats('svg')


# Config variables
root = Path(__file__).parent.resolve()
artifacts = root / 'artifacts'
artifacts.mkdir(exist_ok=True)
runs = root / 'mlruns'
data_path = root / 'data'


class PrepareFeatures(BaseEstimator, TransformerMixin):
    """Prepare features for dict vectorizer."""

    def __init__(self, categorical, numerical):
        self.categorical = categorical
        self.numerical = numerical
        self.features = categorical + numerical

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X['PU_DO'] = X['PULocationID'].astype(str) + '_' + X['DOLocationID'].astype(str)
        X[self.categorical] = X[self.categorical].astype(str)
        X = X[self.features].to_dict(orient='records')
        
        return X


def compute_targets(data):
    """Derive target from pickup and dropoff datetimes."""

    # Create target column and filter outliers
    data['duration'] = data.lpep_dropoff_datetime - data.lpep_pickup_datetime
    data['duration'] = data.duration.dt.total_seconds() / 60

    return data.duration.values


def filter_target_outliers(data, targets, y_min=1, y_max=60):
    """Filter data with targets outside of range."""

    X = data[(data.duration >= y_min) & (data.duration <= y_max)]
    y = X.duration.values

    return X, y


def plot_duration_distribution(model, X_train, y_train, X_valid, y_valid):
    """Plot true and prediction distribution."""
    
    fig, ax = plt.subplots(1, 2, figsize=(8, 3))

    sns.histplot(model.predict(X_train), ax=ax[0], label='pred', color='C0', stat='density', kde=True)
    sns.histplot(y_train, ax=ax[0], label='true', color='C1', stat='density', kde=True)
    ax[0].set_title("Train")
    ax[0].legend()

    sns.histplot(model.predict(X_valid), ax=ax[1], label='pred', color='C0', stat='density', kde=True)
    sns.histplot(y_valid, ax=ax[1], label='true', color='C1', stat='density', kde=True)
    ax[1].set_title("Valid")
    ax[1].legend()

    fig.tight_layout()
    return fig


def preprocess_datasets(train_data_path, valid_data_path):
    """Preprocess datasets for model training and validation. Save pipeline."""

    X_train = pd.read_parquet(train_data_path)
    X_valid = pd.read_parquet(valid_data_path)

    # Compute labels
    y_train = compute_targets(X_train)
    y_valid = compute_targets(X_valid)

    # Filter train and valid (!) data. (i.e. only validate on t=(1, 60) range.)
    X_train, y_train = filter_target_outliers(X_train, y_train)
    X_valid, y_valid = filter_target_outliers(X_valid, y_valid)

    # Feature selection and engineering
    categorical = ['PU_DO']
    numerical = ['trip_distance']

    feature_pipe = make_pipeline(
        PrepareFeatures(categorical, numerical),
        DictVectorizer(),
    )

    # Fit only on train set
    feature_pipe.fit(X_train, y_train)
    X_train = feature_pipe.transform(X_train)
    X_valid = feature_pipe.transform(X_valid)

    # Save preprocessor
    joblib.dump(feature_pipe, artifacts / 'preprocessor.pkl')

    return X_train, y_train, X_valid, y_valid
