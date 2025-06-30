from dataclasses import asdict, dataclass

from fabric import Connection, task


_DOCKER_PULL = "docker pull --platform=linux/amd64"
_DOCKER_BUILD = "docker buildx build --platform=linux/amd64 --build-arg BUILD_DEV=rex"
_DOCKER_RUN = "docker run --platform=linux/amd64"


@dataclass
class EnvValue:
    # Target Host
    DEPLOY_STAGE = "alpha"
    DEPLOY_SSH_HOST = "192.168.200.31"
    DEPLOY_SSH_PORT = 22
    DEPLOY_SSH_USER = "rex"
    DEPLOY_WORK_PATH = "/home/rex/apps/dnsrobocert-plus-nginx"

    # Docker Container Register
    CR_HOST_NAME = "cr.h.rexzhang.com"
    CR_NAME_SPACE = "ray1ex"

    # Docker Image
    DOCKER_BASE_IMAGE_TAG = "cr.rexzhang.com/library/python:3.13-alpine"
    DOCKER_IMAGE_NAME = "dnsrobocert-plus-nginx"

    @property
    def DOCKER_IMAGE_FULL_NAME(self) -> str:
        return f"{self.CR_HOST_NAME}/{self.CR_NAME_SPACE}/{self.DOCKER_IMAGE_NAME}"

    # Docker Container
    CONTAINER_NAME = "dnsrobocert-plus-nginx"
    CONTAINER_GID = 20
    CONTAINER_UID = 501

    def asdict(self) -> dict:
        return asdict(self)


ev = EnvValue()


@task
def docker_pull_base_image(c):
    c.run(f"{_DOCKER_PULL} {ev.DOCKER_BASE_IMAGE_TAG}")
    print("pull docker base image finished.")


@task()
def docker_build(c):
    print("build docker image...")
    c.run(f"{_DOCKER_BUILD} -t {ev.DOCKER_IMAGE_FULL_NAME} .")
    c.run("docker image prune -f")

    print("build finished.")

    c.run("say docker image build finished")


@task
def docker_push_image(c):
    print("push docker image to register...")

    c.run(f"docker push {ev.DOCKER_IMAGE_FULL_NAME}")
    print("push finished.")


@task
def docker_pull_image(c):
    c.run(f"{_DOCKER_PULL} {ev.DOCKER_IMAGE_FULL_NAME}")
    print("pull image finished.")


def _recreate_container(c, container_name: str, docker_run_cmd: str):
    print("startup container...")
    c.run(f"docker container stop {container_name}", warn=True)
    c.run(f"docker container rm {container_name}", warn=True)
    c.run(f"cd {ev.DEPLOY_WORK_PATH} && {docker_run_cmd}")

    print(f"run {container_name} finished")


@task
def docker_test(c):
    c.run(f"mkdir /tmp/{ev.CONTAINER_NAME}", warn=True)

    docker_run_cmd = f"""{_DOCKER_RUN} -dit --restart unless-stopped \
 -u {ev.CONTAINER_UID}:{ev.CONTAINER_GID} \
 -p 10080:10080 -p 10443:10443 \
 -e TZ=Asia/Shanghai \
 -e DNSROBOCERT=disable \
 -e T12F_STAGE=ALPHA \
 -v $(pwd)/examples/http-only:/config \
 -v /tmp/{ev.CONTAINER_NAME}:/data \
 -v /tmp/{ev.CONTAINER_NAME}:/logs \
 --name {ev.CONTAINER_NAME} \
 {ev.DOCKER_IMAGE_FULL_NAME}"""
    _recreate_container(c, ev.CONTAINER_NAME, docker_run_cmd)

    c.run(f"docker container logs -f {ev.CONTAINER_NAME}")


@task
def docker_recreate_container(c):
    c.run(
        "mkdir -p /home/rex/running/dnsrobocert-plus-nginx/logs/dnsrobocert", warn=True
    )

    docker_run_cmd = f"""docker run -dit --restart unless-stopped \
 --dns 192.168.200.12 \
 -u 1000:1000 \
 -p 80:10080 -p 443:10443 -p 636:10636 \
 --env-file container.env \
 -v /home/rex/running/dnsrobocert-plus-nginx/data:/data \
 -v $(pwd)/config:/config \
 -v $(pwd)/data_dnsrobocert_live:/data_dnsrobocert_live \
 -v $(pwd)/scripts:/scripts \
 -v /home/rex/running/dnsrobocert-plus-nginx/logs:/logs \
 -v /home/rex/running/dnsrobocert-plus-nginx/logs/dnsrobocert:/data/dnsrobocert/logs \
 --name {ev.CONTAINER_NAME} \
 --label com.centurylinklabs.watchtower.enable=false \
 {ev.DOCKER_IMAGE_FULL_NAME}"""
    _recreate_container(c, ev.CONTAINER_NAME, docker_run_cmd)

    c.run(f"docker container logs -f {ev.CONTAINER_NAME}")


@task
def build(c):
    docker_pull_base_image(c)
    docker_build(c)


@task
def deploy(c):
    docker_push_image(c)

    conn = Connection(
        host=ev.DEPLOY_SSH_HOST, port=ev.DEPLOY_SSH_PORT, user=ev.DEPLOY_SSH_USER
    )
    docker_pull_image(conn)
    docker_recreate_container(conn)

    print("deploy finished")
    c.run(f"say docker deploy to {ev.DEPLOY_STAGE} finished")
