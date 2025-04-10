docker run --rm \
  -e HTTP_PROXY=http://10.24.241.28:18888/ \
  -e HTTPS_PROXY=http://10.24.241.28:18888/ \
  -v $(pwd):/build xlsx-layer
