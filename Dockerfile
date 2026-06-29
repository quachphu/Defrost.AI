FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir -e ".[infra]" && pip install --no-cache-dir ddgs

EXPOSE 8000

CMD ["uvicorn", "defrosted.rent_vs_buy_app:app", "--host", "0.0.0.0", "--port", "8000"]
