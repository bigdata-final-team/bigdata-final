"""Smoke test: every library imports and a model trains on a toy dataset."""
import lightgbm, matplotlib, numpy, pandas, polars, prophet, pyarrow, scipy, seaborn, sklearn, statsmodels, xgboost
from prophet import Prophet
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

for m in (numpy, pandas, polars, pyarrow, scipy, statsmodels, sklearn, xgboost, lightgbm, prophet, matplotlib, seaborn):
    print(f"{m.__name__:12} {m.__version__}")

X_tr, X_te, y_tr, y_te = train_test_split(*load_iris(return_X_y=True), random_state=0)
acc = RandomForestClassifier(random_state=0).fit(X_tr, y_tr).score(X_te, y_te)
assert acc > 0.9, acc
print(f"iris RF accuracy: {acc:.3f}  OK")

# Prophet fit exercises the bundled CmdStan backend, which is the part that breaks on Windows.
df = pandas.DataFrame({"ds": pandas.date_range("2024-01-01", periods=200), "y": numpy.arange(200) * 0.01})
forecast = Prophet().fit(df).predict(pandas.DataFrame({"ds": pandas.date_range("2024-07-19", periods=30)}))
assert len(forecast) == 30, len(forecast)
print("prophet forecast: 30 days  OK")
