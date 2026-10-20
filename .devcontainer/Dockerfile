FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f AS tool-downloader

COPY .devcontainer/generated/tools.env /tmp/toolchain.env
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    --no-install-recommends ca-certificates curl \
  && set -a && . /tmp/toolchain.env && set +a \
  && architecture="$(dpkg --print-architecture)" \
  && case "$architecture" in \
    amd64) elan_target=x86_64-unknown-linux-gnu; elan_sha256="$ELAN_SHA256_AMD64"; \
      ruff_target=x86_64-unknown-linux-gnu; ruff_sha256="$RUFF_SHA256_AMD64"; \
      shfmt_sha256="$SHFMT_SHA256_AMD64"; latexindent_asset=latexindent-linux; \
      latexindent_sha256="$LATEXINDENT_SHA256_AMD64"; shellcheck_target=x86_64; \
      shellcheck_sha256="$SHELLCHECK_SHA256_AMD64" ;; \
    arm64) elan_target=aarch64-unknown-linux-gnu; elan_sha256="$ELAN_SHA256_ARM64"; \
      ruff_target=aarch64-unknown-linux-gnu; ruff_sha256="$RUFF_SHA256_ARM64"; \
      shfmt_sha256="$SHFMT_SHA256_ARM64"; latexindent_asset=latexindent-linux-arm64; \
      latexindent_sha256="$LATEXINDENT_SHA256_ARM64"; shellcheck_target=aarch64; \
      shellcheck_sha256="$SHELLCHECK_SHA256_ARM64" ;; \
    *) echo "Unsupported architecture: $architecture" >&2; exit 1 ;; esac \
  && mkdir -p /out/bin /tmp/ruff /tmp/shellcheck \
  && curl -fsSL -o /tmp/elan.tgz "https://github.com/leanprover/elan/releases/download/v${ELAN_VERSION}/elan-${elan_target}.tar.gz" \
  && echo "${elan_sha256}  /tmp/elan.tgz" | sha256sum --check - \
  && tar -xzf /tmp/elan.tgz -C /out/bin elan-init \
  && curl -fsSL -o /tmp/ruff.tgz "https://github.com/astral-sh/ruff/releases/download/${RUFF_VERSION}/ruff-${ruff_target}.tar.gz" \
  && echo "${ruff_sha256}  /tmp/ruff.tgz" | sha256sum --check - \
  && tar -xzf /tmp/ruff.tgz -C /tmp/ruff --strip-components=1 \
  && install /tmp/ruff/ruff /out/bin/ruff \
  && curl -fsSL -o /tmp/shfmt "https://github.com/mvdan/sh/releases/download/v${SHFMT_VERSION}/shfmt_v${SHFMT_VERSION}_linux_${architecture}" \
  && echo "${shfmt_sha256}  /tmp/shfmt" | sha256sum --check - \
  && install /tmp/shfmt /out/bin/shfmt \
  && curl -fsSL -o /tmp/latexindent "https://github.com/cmhughes/latexindent.pl/releases/download/V${LATEXINDENT_VERSION}/${latexindent_asset}" \
  && echo "${latexindent_sha256}  /tmp/latexindent" | sha256sum --check - \
  && install /tmp/latexindent /out/bin/latexindent \
  && curl -fsSL -o /tmp/shellcheck.tgz "https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/shellcheck-v${SHELLCHECK_VERSION}.linux.${shellcheck_target}.tar.gz" \
  && echo "${shellcheck_sha256}  /tmp/shellcheck.tgz" | sha256sum --check - \
  && tar -xzf /tmp/shellcheck.tgz -C /tmp/shellcheck --strip-components=1 \
  && install /tmp/shellcheck/shellcheck /out/bin/shellcheck

FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f AS texlive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl perl xz-utils \
  && rm -rf /var/lib/apt/lists/*
COPY .devcontainer/generated/texlive.env /tmp/texlive.env
RUN set -a && . /tmp/texlive.env && set +a \
  && repository="https://texlive.info/tlnet-archive/${TEXLIVE_ARCHIVE_DATE}/tlnet" \
  && curl -fsSL -o /tmp/install-tl.tgz "$repository/install-tl-unx.tar.gz" \
  && echo "${TEXLIVE_INSTALLER_SHA256}  /tmp/install-tl.tgz" | sha256sum --check - \
  && mkdir /tmp/install-tl \
  && tar -xzf /tmp/install-tl.tgz -C /tmp/install-tl --strip-components=1 \
  && printf '%s\n' 'selected_scheme scheme-full' 'instopt_letter 0' \
    'tlpdbopt_autobackup 0' 'tlpdbopt_desktop_integration 0' \
    'tlpdbopt_file_assocs 0' 'tlpdbopt_install_docfiles 0' \
    'tlpdbopt_install_srcfiles 0' > /tmp/install-tl/profile \
  && TEXLIVE_INSTALL_NO_CONTEXT_CACHE=1 TEXLIVE_INSTALL_NO_WELCOME=1 \
    perl /tmp/install-tl/install-tl -profile /tmp/install-tl/profile -repository "$repository" \
  && "/usr/local/texlive/${TEXLIVE_YEAR}/bin/$(uname -m)-linux/tlmgr" remove --force aliascnt \
  && rm -rf /tmp/install-tl /tmp/install-tl.tgz "/usr/local/texlive/${TEXLIVE_YEAR}"/*.log

FROM python:3.14.8-slim-trixie@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170
LABEL org.opencontainers.image.description="AshaIy textbook toolchain"
ENV DEBIAN_FRONTEND=noninteractive
ENV ELAN_HOME=/usr/local/elan
ENV ASHAIY_ROOT=/workspace
ENV PATH="/usr/local/elan/bin:/usr/local/bin:/usr/local/texlive/2026/bin/x86_64-linux:/usr/local/texlive/2026/bin/aarch64-linux:${PATH}"
WORKDIR /workspace
COPY .devcontainer/generated/system.env /tmp/system.env
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates chromium curl ghostscript \
    git git-man jekyll jq less locales man-db nano openssh-client perl \
    poppler-utils ripgrep ruby ruby-bundler tree tzdata xz-utils zsh \
  && set -a && . /tmp/system.env && set +a \
  && mkdir -p -m 755 /etc/apt/keyrings \
  && curl -fsSL -o /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  && echo "${GH_KEYRING_SHA256}  /etc/apt/keyrings/githubcli-archive-keyring.gpg" \
    | sha256sum --check - \
  && chmod 644 /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list \
  && apt-get update && apt-get install -y --no-install-recommends "gh=${GH_VERSION}" \
  && echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen \
  && locale-gen \
  && rm -rf /var/lib/apt/lists/*
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV SHELL=/bin/zsh
ENV EDITOR=nano
ENV TZ=Etc/UTC
ARG BASEDEVCONTAINER_SHELL_COMMIT=eed51b33f4fc5bcb6be2ee566402afeb7be47375
ARG OH_MY_ZSH_COMMIT=146461f7c6d95f4ba1220559d66eb113418b40a8
ARG POWERLEVEL10K_COMMIT=8a676a9157d2b0e00e88d06456ac7317f11c0317
RUN curl -fsSL -o /root/.zshrc \
      "https://raw.githubusercontent.com/qdm12/basedevcontainer/${BASEDEVCONTAINER_SHELL_COMMIT}/shell/.zshrc" \
  && echo 'fd04e2d7c6d9367b2b34d023a335dec44f2fe7b25d0997bbc8bfd0345f26c191  /root/.zshrc' \
    | sha256sum --check - \
  && sed -i -e '10,35d' -e 's|source ~/.zshrc-specific$|source ~/.zshrc-specific.sh|' /root/.zshrc \
  && curl -fsSL -o /root/.p10k.zsh \
      "https://raw.githubusercontent.com/qdm12/basedevcontainer/${BASEDEVCONTAINER_SHELL_COMMIT}/shell/.p10k.zsh" \
  && echo 'ba3e6c86226936f49a08f395fa585f54015958c3fa730fd7a79434b52c2bb724  /root/.p10k.zsh' \
    | sha256sum --check - \
  && git clone --filter=blob:none --no-checkout \
      https://github.com/ohmyzsh/ohmyzsh.git /root/.oh-my-zsh \
  && git -C /root/.oh-my-zsh checkout "$OH_MY_ZSH_COMMIT" \
  && git clone --filter=blob:none --no-checkout \
      https://github.com/romkatv/powerlevel10k.git \
      /root/.oh-my-zsh/custom/themes/powerlevel10k \
  && git -C /root/.oh-my-zsh/custom/themes/powerlevel10k \
      checkout "$POWERLEVEL10K_COMMIT" \
  && rm -rf /root/.oh-my-zsh/.git \
      /root/.oh-my-zsh/custom/themes/powerlevel10k/.git \
  && usermod --shell /bin/zsh root
COPY --from=tool-downloader /out/bin/elan-init /usr/local/bin/elan-init
COPY .devcontainer/generated/lean.env /tmp/lean.env
RUN set -a && . /tmp/lean.env && set +a \
  && /usr/local/bin/elan-init -y --no-modify-path --default-toolchain none \
  && rm /usr/local/bin/elan-init \
  && elan toolchain install "$LEAN_TOOLCHAIN" \
  && elan default "$LEAN_TOOLCHAIN"
COPY .devcontainer/generated/python.env /tmp/python.env
RUN set -a && . /tmp/python.env && set +a \
  && python3 -m pip install \
    --disable-pip-version-check --no-cache-dir --only-binary=:all: \
    "PyYAML==${PYYAML_VERSION}" \
    "playwright==${PLAYWRIGHT_VERSION}" \
    "hypothesis==${HYPOTHESIS_VERSION}" \
    "coverage==${COVERAGE_VERSION}" \
    "basedpyright==${BASEDPYRIGHT_VERSION}" \
    "yamllint==${YAMLLINT_VERSION}" \
    "djlint==${DJLINT_VERSION}" \
    "check-jsonschema==${CHECK_JSONSCHEMA_VERSION}"
COPY --from=tool-downloader /out/bin/ruff /out/bin/shfmt \
    /out/bin/latexindent /out/bin/shellcheck /usr/local/bin/
COPY --from=texlive /usr/local/texlive /usr/local/texlive
COPY scripts/ashaiy_launcher.sh /usr/local/bin/ashaiy
COPY config/toolchain.env /workspace/config/toolchain.env
COPY scripts/check_toolchain.sh /workspace/scripts/check_toolchain.sh
RUN set -a && . /workspace/config/toolchain.env && set +a \
  && lualatex --version | head -n1 | grep -F "TeX Live ${TEXLIVE_YEAR}" \
  && ./scripts/check_toolchain.sh
ENTRYPOINT []
CMD ["/bin/zsh"]
