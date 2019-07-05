from envparse import env


settings = {
    "name": "Nicecream FM History",
    "version": "1.0.0",
    "debug": env("API_DEBUG", cast=bool, default=False),
    "environment": env("API_ENVIRONMENT", default="production"),
    "postgres": {
        "url": None,
        "host": env("PGHOST", default=None),
        "port": env("PGPORT", cast=int, default=None),
        "user": env("PGUSER", default=None),
        "password": env("PGPASSWORD", default=None),
        "database": env("PGDATABASE", default=None)
    },
    "redis": {
        "url": None,
        "host": env("REDIS_HOST", default=None),
        "port": env("REDIS_PORT", cast=int, default=None),
        "database": env("REDIS_DB", cast=int, default=0),
        "channel": env("REDIS_CHANNEL", default="history"),
    },
    "pagination": {
        "limit": 50
    },
    "crawler": {
        "interval": env("API_CRAWLER_INTERVAL", cast=int, default=30),
        "backoff_interval": env("API_CRAWLER_BACKOFF_INTERVAL", cast=int, default=300),
        "headers": {
            "User-Agent": env("API_CRAWLER_AGENT", default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) "
                                                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                                                           "Safari/537.36")
        }
    },
    "openapi": {
        "server": {
            "url": env("API_OPENAPI_SERVER_URL", default="http://localhost:8080")
        },
        "route": {
            "url": "/openapi.json",
            "name": "openapi"
        }
    },
    "sse": {
        "retry": 30
    },
    "cors": env("API_CORS_ALLOWED", cast=bool, default=False),
    "server": {
        "host": env("API_SERVER_HOST", default="127.0.0.1"),
        "port": env("API_SERVER_PORT", cast=int, default=8080)
    },
    "spa": {
        "url": env("SPA_URL", default=None)
    },
    "session": {
        "cookie": {
            "secret_key": env("API_COOKIE_SESSION_SECRET_KEY", default=None),
            "cookie_name": "nicecream_history",
            "secure": env("API_COOKIE_SESSION_SECURE", cast=bool, default=True)
        }
    },
    "oauth2": {
        "google": {
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "client_id": env("API_GOOGLE_CLIENT_ID", default=None),
            "client_secret": env("API_GOOGLE_CLIENT_SECRET", default=None),
            "redirect_url": env("API_GOOGLE_REDIRECT_URL", default=None)
        }
    }
}

assert settings["postgres"]["host"] is not None
assert settings["postgres"]["port"] is not None
assert settings["postgres"]["user"] is not None
assert settings["postgres"]["password"] is not None
assert settings["postgres"]["database"] is not None
assert settings["redis"]["host"] is not None
assert settings["redis"]["port"] is not None
assert settings["redis"]["database"] is not None
assert settings["spa"]["url"] is not None
assert settings["session"]["cookie"]["secret_key"] is not None
assert settings["oauth2"]["google"]["client_id"] is not None
assert settings["oauth2"]["google"]["client_secret"] is not None
assert settings["oauth2"]["google"]["redirect_url"] is not None


settings["postgres"]["url"] = "postgresql://{user}:{password}@{host}:{port}/{database}".format(**settings["postgres"])
settings["redis"]["url"] = "redis://{host}:{port}?db={database}".format(**settings["redis"])
