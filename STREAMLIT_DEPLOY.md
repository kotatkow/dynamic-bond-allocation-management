# Streamlit Deployment

This repository includes a Streamlit entry point at `streamlit_app.py`.

## Local Run

If Python and Streamlit are installed:

```powershell
streamlit run streamlit_app.py
```

If Streamlit is not installed locally:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

## Streamlit Community Cloud

1. Go to [Streamlit Community Cloud](https://share.streamlit.io/).
2. Click `Create app`.
3. Choose the GitHub repository `kotatkow/dynamic-bond-allocation-management`.
4. Set the main file path to `streamlit_app.py`.
5. Deploy.

Streamlit's official docs say Community Cloud deploys from a GitHub repository and uses dependency files such as `requirements.txt` to install Python packages.

## Secrets

For authenticated market data, add these secrets in the Streamlit app settings:

```toml
FRED_API_KEY = "your-fred-key"
ALPHA_VANTAGE_API_KEY = "your-alpha-vantage-key"
```

Without secrets, the app will still run with a clearly labeled demo market-data snapshot.

For local development, copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and paste your real keys there. The real `secrets.toml` file is ignored by Git and must not be committed.
