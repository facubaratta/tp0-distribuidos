 #!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Uso: $0 <archivo_salida.yaml> <cantidad_clientes>" >&2
  exit 1
fi

out_file="$1"
clients="$2"

echo "Nombre del archivo de salida: $out_file"
echo "Cantidad de clientes: $clients"

python3 generar-compose.py "$out_file" "$clients"