FROM public.ecr.aws/lambda/python:3.11

# Add proxy environment variables that will be used during build
ARG HTTP_PROXY
ARG HTTPS_PROXY
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV http_proxy=${HTTP_PROXY}
ENV https_proxy=${HTTPS_PROXY}

# Configure yum to use proxy
RUN if [ -n "$HTTP_PROXY" ]; then \
    echo "proxy=$HTTP_PROXY" >> /etc/yum.conf; \
    fi

# Install necessary build tools
RUN yum install -y gcc gcc-c++ libxml2-devel libxslt-devel zip unzip

WORKDIR /build

# Copy your script to build the layer
COPY build_layer.sh .
RUN chmod +x build_layer.sh

ENTRYPOINT ["/bin/bash"]
CMD ["./build_layer.sh"]
