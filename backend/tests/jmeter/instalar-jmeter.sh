#!/usr/bin/env bash
# Instala Apache JMeter en ./herramientas/ (sin root, solo descomprimir).
# Uso: bash backend/tests/jmeter/instalar-jmeter.sh
set -euo pipefail

VERSION="${JMETER_VERSION:-5.6.3}"
DESTINO="${JMETER_DIR:-$HOME/herramientas}"
TGZ="apache-jmeter-${VERSION}.tgz"
URL="https://archive.apache.org/dist/jmeter/binaries/${TGZ}"

mkdir -p "$DESTINO"
cd "$DESTINO"

if [ -x "apache-jmeter-${VERSION}/bin/jmeter" ]; then
  echo ">> JMeter ${VERSION} ya está en $DESTINO/apache-jmeter-${VERSION}"
else
  echo ">> Descargando JMeter ${VERSION} ..."
  curl -fL -o "$TGZ" "$URL"
  echo ">> Descomprimiendo ..."
  tar xzf "$TGZ"
  rm -f "$TGZ"
  echo ">> Instalado en $DESTINO/apache-jmeter-${VERSION}"
fi

echo
echo "Para usarlo en esta terminal:"
echo "  export PATH=\"$DESTINO/apache-jmeter-${VERSION}/bin:\$PATH\""
echo "  jmeter --version"
