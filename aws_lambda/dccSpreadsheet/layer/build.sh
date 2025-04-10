docker build \
  --build-arg HTTP_PROXY=http://10.24.241.28:18888/ \
  --build-arg HTTPS_PROXY=http://10.24.241.28:18888/ \
  -t xlsx-layer .
