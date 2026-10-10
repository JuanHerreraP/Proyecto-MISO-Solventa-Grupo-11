FROM python:3.12-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend principal de Solventa
COPY app ./app

# Proveedores simulados
COPY mocks ./mocks

# Backend principal
ENV PORT=8000

# Proveedor A KYC seleccionado
ENV KYC_PROVIDER=A

# URLs de los proveedores simulados
ENV KYC_PROVIDER_A_URL=http://127.0.0.1:8001
# ENV KYC_PROVIDER_B_URL=http://127.0.0.1:8002
# ENV KYC_PROVIDER_C_URL=http://127.0.0.1:8003

# Puertos disponibles
EXPOSE 8000
EXPOSE 8001
# EXPOSE 8002
# EXPOSE 8003

# Levanta Provider A y luego Solventa.
# Solventa queda como proceso principal del contenedor.
CMD ["sh", "-c", "uvicorn mocks.kyc.provider_a:app --host 0.0.0.0 --port 8001 & uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

# Para utilizar Provider B en vez de A:
# CMD ["sh", "-c", "uvicorn mocks.kyc.provider_b:app --host 0.0.0.0 --port 8002 & uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

# Para utilizar Provider C en vez de A:
# CMD ["sh", "-c", "uvicorn mocks.kyc.provider_c:app --host 0.0.0.0 --port 8003 & uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]