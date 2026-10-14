# Optional Dockerfile for future deployment. Not required for local development.
# Build: docker build -t gtmos .
# Run:   docker run -p 8000:8000 -p 8501:8501 gtmos

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV LLM_MODE=mock
ENV DATABASE_URL=sqlite:///./gtmos.db

EXPOSE 8000 8501

CMD ["sh", "-c", "uvicorn app.api.main:app --host 0.0.0.0 --port 8000 & streamlit run app/dashboard/home.py --server.port 8501 --server.headless true"]
