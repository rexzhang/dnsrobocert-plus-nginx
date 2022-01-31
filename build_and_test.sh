docker container stop dnsrobocert
docker container rm dnsrobocert
docker image rm ray1ex/dnsrobocert

docker pull python:3.9-alpine
docker build -t ray1ex/dnsrobocert . --build-arg ENV=rex


mkdir /tmp/data
docker run -dit -p 0.0.0.0:3141:3141 -v /tmp/data:/data \
  -e UID=501 -e GID=20 \
  --name dnsrobocert ray1ex/dnsrobocert
docker image prune -f
docker container logs -f dnsrobocert
