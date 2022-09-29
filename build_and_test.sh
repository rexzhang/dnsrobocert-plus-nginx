docker container stop dnsrobocert
docker container rm dnsrobocert
docker image rm ray1ex/dnsrobocert

docker pull python:3.9-alpine
docker build -t ray1ex/dnsrobocert . --build-arg ENV=rex


mkdir /tmp/dnsrobocert-data
mkdir /tmp/dnsrobocert-nginx
docker run -dit --restart unless-stopped \
  -e UID=501 -e GID=20 \
  -v /tmp/dnsrobocert.yml:/etc/dnsrobocert.yml \
  -v /tmp/dnsrobocert-data:/data \
  -v /tmp/dnsrobocert-nginx:/nginx \
  --name dnsrobocert ray1ex/dnsrobocert
docker image prune -f
docker container logs -f dnsrobocert
