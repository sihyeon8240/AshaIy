FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS tool-downloader

COPY --chmod=0644 .devcontainer/generated/tools.env /tmp/toolchain.env
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    --no-install-recommends ca-certificates curl \
  && set -a && . /tmp/toolchain.env && set +a \
  && architecture="$(dpkg --print-architecture)" \
  && case "$architecture" in \
    amd64) \
      elan_target=x86_64-unknown-linux-gnu; \
      elan_sha256="$ELAN_SHA256_AMD64"; \
      ruff_target=x86_64-unknown-linux-gnu; \
      ruff_sha256="$RUFF_SHA256_AMD64"; \
      shfmt_sha256="$SHFMT_SHA256_AMD64"; \
      latexindent_asset=latexindent-linux; \
      latexindent_sha256="$LATEXINDENT_SHA256_AMD64"; \
      shellcheck_target=x86_64; \
      shellcheck_sha256="$SHELLCHECK_SHA256_AMD64"; \
      gh_sha256="$GH_SHA256_AMD64" \
      ;; \
    arm64) \
      elan_target=aarch64-unknown-linux-gnu; \
      elan_sha256="$ELAN_SHA256_ARM64"; \
      ruff_target=aarch64-unknown-linux-gnu; \
      ruff_sha256="$RUFF_SHA256_ARM64"; \
      shfmt_sha256="$SHFMT_SHA256_ARM64"; \
      latexindent_asset=latexindent-linux-arm64; \
      latexindent_sha256="$LATEXINDENT_SHA256_ARM64"; \
      shellcheck_target=aarch64; \
      shellcheck_sha256="$SHELLCHECK_SHA256_ARM64"; \
      gh_sha256="$GH_SHA256_ARM64" \
      ;; \
    *) \
      echo "Unsupported architecture: $architecture" >&2; \
      exit 1 \
      ;; \
    esac \
  && mkdir -p /out/bin /tmp/ruff /tmp/shellcheck /tmp/gh \
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
  && install /tmp/shellcheck/shellcheck /out/bin/shellcheck \
  && curl -fsSL -o /tmp/gh.tgz "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${architecture}.tar.gz" \
  && echo "${gh_sha256}  /tmp/gh.tgz" | sha256sum --check - \
  && tar -xzf /tmp/gh.tgz -C /tmp/gh --strip-components=1 \
  && install /tmp/gh/bin/gh /out/bin/gh

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS texlive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl libfontconfig1 perl xz-utils \
  && rm -rf /var/lib/apt/lists/*
COPY --chmod=0644 .devcontainer/generated/texlive.env /tmp/texlive.env
COPY --chmod=0644 config/texlive.profile config/texlive-packages.txt /tmp/
RUN set -a && . /tmp/texlive.env && set +a \
  && repository="https://texlive.info/tlnet-archive/${TEXLIVE_ARCHIVE_DATE}/tlnet" \
  && curl -fsSL -o /tmp/install-tl.tgz "$repository/install-tl-unx.tar.gz" \
  && echo "${TEXLIVE_INSTALLER_SHA256}  /tmp/install-tl.tgz" | sha256sum --check - \
  && mkdir /tmp/install-tl \
  && tar -xzf /tmp/install-tl.tgz -C /tmp/install-tl --strip-components=1 \
  && cp /tmp/texlive.profile /tmp/install-tl/profile \
  && printf 'TEXDIR /usr/local/texlive/%s\n' "$TEXLIVE_YEAR" >> /tmp/install-tl/profile \
  && TEXLIVE_INSTALL_NO_CONTEXT_CACHE=1 TEXLIVE_INSTALL_NO_WELCOME=1 \
    perl /tmp/install-tl/install-tl -profile /tmp/install-tl/profile -repository "$repository" \
  && tex_bin="$(find "/usr/local/texlive/${TEXLIVE_YEAR}/bin" -mindepth 1 -maxdepth 1 -type d)" \
  && export PATH="$tex_bin:$PATH" \
  && xargs -r tlmgr --repository "$repository" install < /tmp/texlive-packages.txt \
  && TEXMFCACHE="/usr/local/texlive/${TEXLIVE_YEAR}/texmf-var" \
    "$tex_bin/luaotfload-tool" --update --force \
  && rm -rf /tmp/install-tl /tmp/install-tl.tgz "/usr/local/texlive/${TEXLIVE_YEAR}"/*.log

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS ruby-tools

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates g++ make ruby ruby-dev \
  && rm -rf /var/lib/apt/lists/*
COPY --chmod=0644 .devcontainer/generated/ruby.env /tmp/ruby.env
COPY --chmod=0644 .devcontainer/generated/Gemfile /tmp/Gemfile
COPY --chmod=0644 config/Gemfile.lock /tmp/Gemfile.lock
RUN set -a && . /tmp/ruby.env && set +a \
  && gem install --no-document "bundler:${BUNDLER_VERSION}" \
  && cd /tmp && BUNDLE_FROZEN=true bundle install

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS lean-toolchain
ENV ELAN_HOME=/usr/local/elan
ENV PATH="/usr/local/elan/bin:${PATH}"
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*
COPY --from=tool-downloader --chmod=0755 /out/bin/elan-init /usr/local/bin/elan-init
COPY --chmod=0644 .devcontainer/generated/lean.env /tmp/lean.env
RUN set -a && . /tmp/lean.env && set +a \
  && /usr/local/bin/elan-init -y --no-modify-path --default-toolchain none \
  && rm /usr/local/bin/elan-init \
  && elan toolchain install "$LEAN_TOOLCHAIN" \
  && elan default "$LEAN_TOOLCHAIN"

FROM python:3.14.10-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS pdf
LABEL org.opencontainers.image.description="PDF build toolchain for AshaIy mathematics textbooks, including TeX Live and Python."
ENV DEBIAN_FRONTEND=noninteractive
ENV ASHAIY_ROOT=/workspace
ENV PATH="/usr/local/texlive/2026/bin/x86_64-linux:/usr/local/texlive/2026/bin/aarch64-linux:${PATH}"
WORKDIR /workspace
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl ghostscript git locales perl poppler-utils util-linux xz-utils \
  && echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen \
  && locale-gen \
  && rm -rf /var/lib/apt/lists/*
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV TZ=Etc/UTC
COPY --chmod=0644 .devcontainer/generated/pdf.env /tmp/python.env
RUN set -a && . /tmp/python.env && set +a \
  && python3 -m pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: \
    "PyYAML==${PYYAML_VERSION}"
COPY --from=texlive /usr/local/texlive /usr/local/texlive
COPY --chmod=0755 scripts/ashaiy_launcher.sh /usr/local/bin/ashaiy
COPY --chmod=0644 .devcontainer/generated/pdf.env /workspace/config/toolchain.env
COPY --chmod=0755 scripts/toolchain/check_toolchain.sh /workspace/scripts/toolchain/check_toolchain.sh
RUN set -a && . /workspace/config/toolchain.env && set +a \
  && lualatex --version | head -n1 | grep -F "TeX Live ${TEXLIVE_YEAR}" \
  && ./scripts/toolchain/check_toolchain.sh pdf
COPY --chmod=0644 scripts/toolchain/inventory.py /usr/local/bin/ashaiy-inventory.py
RUN python3 /usr/local/bin/ashaiy-inventory.py --output /usr/local/share/ashaiy/inventory.json
ENTRYPOINT []
CMD ["/bin/bash"]

FROM pdf AS dev
LABEL org.opencontainers.image.description="Development and CI toolchain for AshaIy mathematics textbooks, including TeX Live, Lean, and Python."
ENV ELAN_HOME=/usr/local/elan
ENV PATH="/usr/local/elan/bin:${PATH}"
ENV SHELL=/bin/zsh
ENV EDITOR=nano
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium git-man jq less man-db nano openssh-client ripgrep ruby tree zsh \
  && rm -rf /var/lib/apt/lists/*
COPY --from=lean-toolchain /usr/local/elan /usr/local/elan
COPY --chmod=0644 config/toolchain.env /workspace/config/toolchain.env
COPY --from=ruby-tools /var/lib/gems /var/lib/gems
COPY --from=ruby-tools /usr/local/bin/ /usr/local/bin/
COPY --chmod=0644 .devcontainer/generated/python.env /tmp/python.env
COPY --chmod=0644 .github/requirements-ci.txt /tmp/requirements-ci.txt
RUN set -a && . /tmp/python.env && set +a \
  && python3 -m pip install \
    --disable-pip-version-check --no-cache-dir --only-binary=:all: \
    --requirement /tmp/requirements-ci.txt
COPY --from=tool-downloader --chmod=0755 /out/bin/ruff /out/bin/shfmt \
    /out/bin/latexindent /out/bin/shellcheck /out/bin/gh /usr/local/bin/
ARG BASEDEVCONTAINER_SHELL_COMMIT=08ecc2ae6dcda53eb59a7edd8246682f3e0a4238
ARG OH_MY_ZSH_COMMIT=6010fb6260f359e71d99ba25f05f9215809b3ed2
ARG POWERLEVEL10K_COMMIT=433bb250037d1baf479adf06ce78b3a338c574a4
RUN curl -fsSL -o /root/.zshrc \
      "https://raw.githubusercontent.com/qdm12/basedevcontainer/${BASEDEVCONTAINER_SHELL_COMMIT}/shell/.zshrc" \
  && echo '2dc482cee05c94bc7c63afd8a75e260637a0db73df76f667d196e2f1c08ef30f  /root/.zshrc' \
    | sha256sum --check - \
  && sed -i \
    -e '/^# SSH directory check$/,/^# Enable Powerlevel10k instant prompt\./{ /^# Enable Powerlevel10k instant prompt\./!d; }' \
    -e 's|source ~/.zshrc-specific$|source ~/.zshrc-specific.sh|' /root/.zshrc \
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
RUN ./scripts/toolchain/check_toolchain.sh
RUN python3 /usr/local/bin/ashaiy-inventory.py --output /usr/local/share/ashaiy/inventory.json
CMD ["/bin/zsh"]
