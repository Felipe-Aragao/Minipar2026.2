"""Cliente TCP incorporado somente em programas que usam fork host."""

CPP_REMOTE = r"""
#include <iomanip>
#ifndef _WIN32
#include <fcntl.h>
#endif

template<typename T>
int __remote_int(T value) {
    if constexpr (std::is_arithmetic_v<T>) {
        double number = static_cast<double>(value);
        if (std::isfinite(number) && std::trunc(number) == number &&
            number >= std::numeric_limits<int>::min() &&
            number <= std::numeric_limits<int>::max())
            return static_cast<int>(number);
    }
    throw std::runtime_error("fork host requer argumentos inteiros de 32 bits");
}

inline double __remote_call(const std::string& ip, int port, std::string request) {
    sockaddr_in address{};
    address.sin_family = AF_INET;
    if (port < 1 || port > 65535 ||
        inet_pton(AF_INET, ip.c_str(), &address.sin_addr) != 1)
        throw std::runtime_error("fork host requer endereco IPv4 e porta valida");
    address.sin_port = htons(static_cast<unsigned short>(port));

#ifdef _WIN32
    const auto invalid = INVALID_SOCKET;
    const DWORD timeout = 10000;
#else
    const int invalid = -1;
    const timeval timeout{10, 0};
#endif
    struct Connection {
        decltype(::socket(AF_INET, SOCK_STREAM, 0)) fd;
        ~Connection() { CLOSE_SOCK(fd); }
    };
    const auto fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd == invalid) throw std::runtime_error("fork host: falha ao criar socket");
    Connection connection{fd};
    for (int option : {SO_RCVTIMEO, SO_SNDTIMEO}) {
        if (setsockopt(fd, SOL_SOCKET, option,
                       reinterpret_cast<const char*>(&timeout), sizeof(timeout)) != 0)
            throw std::runtime_error("fork host: falha ao configurar timeout");
    }
#ifdef _WIN32
    u_long mode = 1;
    if (ioctlsocket(fd, FIONBIO, &mode) != 0)
        throw std::runtime_error("fork host: falha ao configurar conexao");
#else
    const int mode = fcntl(fd, F_GETFL);
    if (mode < 0 || fd >= FD_SETSIZE || fcntl(fd, F_SETFL, mode | O_NONBLOCK) < 0)
        throw std::runtime_error("fork host: falha ao configurar conexao");
#endif
    if (connect(fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0) {
        fd_set ready;
        FD_ZERO(&ready);
        FD_SET(fd, &ready);
        timeval limit{3, 0};
        int error = 0;
#ifdef _WIN32
        fd_set failed = ready;
        int size = sizeof(error);
        const auto status = select(0, nullptr, &ready, &failed, &limit);
#else
        socklen_t size = sizeof(error);
        const auto status = select(fd + 1, nullptr, &ready, nullptr, &limit);
#endif
        if (status <= 0 ||
            getsockopt(fd, SOL_SOCKET, SO_ERROR, reinterpret_cast<char*>(&error), &size) != 0 ||
            error != 0)
            throw std::runtime_error("fork host: worker indisponivel");
    }
#ifdef _WIN32
    mode = 0;
    if (ioctlsocket(fd, FIONBIO, &mode) != 0)
        throw std::runtime_error("fork host: falha ao restaurar conexao");
#else
    if (fcntl(fd, F_SETFL, mode) < 0)
        throw std::runtime_error("fork host: falha ao restaurar conexao");
#endif
    request += '\n';
#ifdef _WIN32
    const int send_flags = 0;
#else
    const int send_flags = MSG_NOSIGNAL;
#endif
    for (std::size_t offset = 0; offset < request.size();) {
        const auto sent = send(fd, request.data() + offset,
                               static_cast<int>(request.size() - offset), send_flags);
        if (sent <= 0) throw std::runtime_error("fork host: falha no envio");
        offset += sent;
    }
    std::string reply;
    char byte;
    while (reply.size() < 256 && recv(fd, &byte, 1, 0) == 1) {
        if (byte == '\n') {
            if (reply.starts_with("OK ")) {
                std::istringstream value(reply.substr(3));
                double result;
                if (value >> result && value.eof() && std::isfinite(result)) return result;
            }
            throw std::runtime_error("fork host: " + reply);
        }
        reply += byte;
    }
    throw std::runtime_error("fork host: resposta ausente ou invalida");
}

inline std::shared_future<double> __remote_fork(
    const std::string& ip, int port, std::string request) {
    return __register_task(std::async(std::launch::async, __remote_call,
                                      ip, port, std::move(request)));
}

inline std::shared_future<double> __remote_fork(
    const std::shared_ptr<MiniParChannel>& channel, std::string request) {
    return __remote_fork(channel->ip, channel->port, std::move(request));
}
"""
