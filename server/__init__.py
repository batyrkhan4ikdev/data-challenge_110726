from dotenv import load_dotenv

# Every entry point (app, scripts, bench) imports `server.*`, so `.env` is loaded once here.
load_dotenv(override=False)