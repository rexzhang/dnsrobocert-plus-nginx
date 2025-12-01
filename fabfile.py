from dataclasses import asdict, dataclass

from fabric import Connection, task
from invoke.context import Context

_DOCKER_PULL = "docker pull --platform=linux/amd64"
_DOCKER_BUILD = "docker buildx build --platform=linux/amd64 --build-arg BUILD_DEV=rex"  # TODO: t-string
_DOCKER_RUN = "docker run --platform=linux/amd64"
_c = Context()


def say_it(message: str):
    print(message)
    _c.run(f"say {message}")


@task
def docker_pull_base_image(c):
    c.run(f"{_DOCKER_PULL} {ev.DOCKER_BASE_IMAGE}")
    print("pull docker base image finished.")


@task
def build(c):
    docker_pull_base_image(c)
    docker_build(c)


@task
def docker_push_image(c):
    print("push docker image to register...")

    c.run(f"docker push {ev.DOCKER_IMAGE_FULL_NAME}")
    say_it("push finished.")


@task
def docker_pull_image(c):
    c.run(f"{_DOCKER_PULL} {ev.DOCKER_IMAGE_FULL_NAME}")
    say_it("pull image finished.")


@task
def docker_send_image(c):
    print("send docker image to deploy server...")
    c.run(
        f'docker save {ev.DOCKER_IMAGE_FULL_NAME} | gzip | ssh {ev.DEPLOY_SSH_USER}@{ev.DEPLOY_SSH_HOST} -p {ev.DEPLOY_SSH_PORT} "gunzip | docker load"'
    )
    say_it("send image finished")


def _recreate_container(c, container_name: str, docker_run_cmd: str):
    if ev.DEPLOY_STAGE == "local":
        c.run(f"mkdir {ev.DEPLOY_WORK_PATH}", warn=True)

    c.run(f"docker container stop {container_name}", warn=True)
    c.run(f"docker container rm {container_name}", warn=True)
    c.run(f"cd {ev.DEPLOY_WORK_PATH} && {docker_run_cmd}")

    say_it(f"deploy {container_name} finished")


@dataclass
class EnvValue:
    APP_NAME = "dnsrobocert-plus-nginx"

    # Target Host
    DEPLOY_STAGE = "dev"
    DEPLOY_SSH_HOST = "dev.h.rexzhang.com"
    DEPLOY_SSH_PORT = 22
    DEPLOY_SSH_USER = "root"
    DEPLOY_WORK_PATH = "/root/dnsrobocert-plus-nginx"

    # Docker Container Register
    CR_HOST_NAME = "cr.h.rexzhang.com"
    CR_NAME_SPACE = "rex"

    # Docker Image
    DOCKER_BASE_IMAGE = "python:3.13-alpine"

    @property
    def DOCKER_IMAGE_FULL_NAME(self) -> str:
        name = f"{self.CR_HOST_NAME}/{self.CR_NAME_SPACE}/{self.APP_NAME}"
        if self.DEPLOY_STAGE != "prd":
            name += f":{self.DEPLOY_STAGE}"

        return name

    # Docker Container
    def get_container_name(self, module: str | None = None) -> str:
        if module is None:
            return f"{self.APP_NAME}-{self.DEPLOY_STAGE}"

        return f"{self.APP_NAME}-{self.DEPLOY_STAGE}-{module}"

    # Docker Container
    CONTAINER_GID = 1000
    CONTAINER_UID = 1000

    def asdict(self) -> dict:
        return asdict(self)

    def switch_env_test(self):
        self.DEPLOY_STAGE = "test"
        self.DEPLOY_WORK_PATH = "/home/rex/dnsrobocert-plus-nginx"


ev = EnvValue()


@task()
def docker_build(c):
    print("build docker image...")
    c.run(f"{_DOCKER_BUILD} -t {ev.DOCKER_IMAGE_FULL_NAME} .")

    say_it("docker image build finished")


@task
def docker_test(c):
    c.run(f"mkdir /tmp/{ev.get_container_name()}", warn=True)

    docker_run_cmd = f"""{_DOCKER_RUN} -dit --restart unless-stopped \
 -u {ev.CONTAINER_UID}:{ev.CONTAINER_GID} \
 -p 10080:10080 -p 10443:10443 \
 -e TZ=Asia/Shanghai \
 -e DNSROBOCERT=disable \
 -e T12F_STAGE=ALPHA \
 -v $(pwd)/examples/nginx.toml:/config/nginx.toml \
 -v /tmp/{ev.get_container_name()}:/data \
 -v /tmp/{ev.get_container_name()}:/logs \
 --name {ev.get_container_name()} \
 {ev.DOCKER_IMAGE_FULL_NAME}"""
    _recreate_container(c, ev.get_container_name(), docker_run_cmd)

    c.run(f"docker container logs -f {ev.get_container_name()}")


@task
def docker_recreate_container(c):
    c.run(
        "mkdir -p /home/rex/running/dnsrobocert-plus-nginx/logs/dnsrobocert", warn=True
    )

    docker_run_cmd = f"""docker run -dit --restart unless-stopped \
 -u {ev.CONTAINER_UID}:{ev.CONTAINER_GID} \
 --network server \
 -p 80:10080 -p 443:10443 -p 636:10636 \
 --env-file container.env \
 -v /home/rex/running/dnsrobocert-plus-nginx/data:/data \
 -v $(pwd)/config:/config \
 -v $(pwd)/data_dnsrobocert_live:/data_dnsrobocert_live \
 -v $(pwd)/scripts:/scripts \
 -v /home/rex/running/dnsrobocert-plus-nginx/logs:/logs \
 -v /home/rex/running/dnsrobocert-plus-nginx/logs/dnsrobocert:/data/dnsrobocert/logs \
 --name {ev.get_container_name()} \
 --label com.centurylinklabs.watchtower.enable=false \
 {ev.DOCKER_IMAGE_FULL_NAME}"""
    _recreate_container(c, ev.get_container_name(), docker_run_cmd)

    c.run(f"docker container logs -f {ev.get_container_name()}")


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
