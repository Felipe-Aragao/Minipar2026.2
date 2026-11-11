# Cabeçalho incorporado ao C++ gerado. A afinidade usa a API do sistema operacional.
# A lista por thread guarda futuros para a barreira join. Ela não mantém threads de trabalho.
# MiniParChannel abre uma conexão TCP por mensagem e confirma a recepção antes de fechá-la.
_CPP_HEADER = """\
#include <iostream>
#include <string>
#include <sstream>
#include <syncstream>
#include <vector>
#include <thread>
#include <future>
#include <memory>
#include <cstring>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <type_traits>
#include <cstdio>
#include <stdexcept>
#include <limits>
#include <mutex>
#include <functional>
#include <fstream>
#include <filesystem>
#include <cstdint>

#ifdef _WIN32
  #ifndef NOMINMAX
    #define NOMINMAX
  #endif
  #include <winsock2.h>
  #include <ws2tcpip.h>
  #include <windows.h>
  #include <shellapi.h>
  #pragma comment(lib, "ws2_32.lib")
  #define CLOSE_SOCK closesocket
#else
  #include <sys/socket.h>
  #include <arpa/inet.h>
  #include <unistd.h>
  #include <pthread.h>
  #include <sched.h>
  #define CLOSE_SOCK close
#endif

// Helper para afinidade de nucleos da CPU (Core Affinity)
inline void __set_core_affinity(int core_id) {
    if (core_id < 0) return;
    unsigned int total_cores = std::thread::hardware_concurrency();
    if (total_cores == 0) total_cores = 1;
    int safe_core = core_id % static_cast<int>(total_cores);
#ifdef _WIN32
    DWORD_PTR mask = (static_cast<DWORD_PTR>(1) << (safe_core % 64));
    DWORD_PTR prev = SetThreadAffinityMask(GetCurrentThread(), mask);
    if (prev == 0) {
        std::cerr << "[AVISO AFINIDADE] Falha ao definir afinidade para nucleo " << safe_core << " no Windows." << std::endl;
    }
#elif defined(__linux__)
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(safe_core, &cpuset);
    int ret = pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
    if (ret != 0) {
        std::cerr << "[AVISO AFINIDADE] Falha ao definir afinidade para nucleo " << safe_core << " no Linux (erro " << ret << ")." << std::endl;
    }
#endif
}

// Pool de tarefas com escopo local por thread para sincronizacao segura com barreira (join;)
inline thread_local std::vector<std::function<void()>> __task_pool;

template<typename T>
std::shared_future<T> __register_task(std::future<T> fut) {
    auto sf = fut.share();
    __task_pool.push_back([sf]() mutable {
        if (sf.valid()) sf.get();
    });
    return sf;
}

template<typename T>
std::shared_future<T> __register_task(std::shared_future<T> sf) {
    __task_pool.push_back([sf]() mutable {
        if (sf.valid()) sf.get();
    });
    return sf;
}

inline void __task_pool_wait_all() {
    std::vector<std::function<void()>> tasks = std::move(__task_pool);
    __task_pool.clear();
    std::exception_ptr error;
    for (auto& task : tasks) {
        try { task(); }
        catch (...) { if (!error) error = std::current_exception(); }
    }
    if (error) std::rethrow_exception(error);
}

// Helper para captura segura do retorno de tarefas (evita erro com tarefas de retorno void)
template<typename Fut>
auto __minipar_get(Fut&& f) {
    using ResultT = decltype(f.get());
    if constexpr (std::is_void_v<ResultT>) {
        if (f.valid()) f.get();
        return 0;
    } else {
        return f.get();
    }
}

// Helper para sincronizacao de tarefas com argumentos join(t), temporarios join(fork ...) ou colecoes
template<typename T>
void __minipar_join_target(T&& target) {
    if constexpr (requires { target.valid(); target.wait(); }) {
        if (target.valid()) target.get();
    } else if constexpr (requires { std::begin(target); std::end(target); }) {
        for (auto& item : target) {
            __minipar_join_target(item);
        }
    }
}

// Helper para Random nativo
double random_val() { return (double)rand() / RAND_MAX; }

// Helper para captura de tempo de alta precisao (em segundos)
double __minipar_time() {
    auto now = std::chrono::high_resolution_clock::now();
    return std::chrono::duration<double>(now.time_since_epoch()).count();
}

// Função nativa para formatação decimal do MiniPar
std::string __fmt(double value, int decimal_places) {
    char buffer[128];
    snprintf(buffer, sizeof(buffer), "%.*f", decimal_places, value);
    return std::string(buffer);
}

// Helper nativo para exportar matriz bidimensional para arquivo BMP (24 bits True Color)
template<typename T>
int __minipar_save_bmp(const std::string& path, const std::vector<std::vector<T>>& mat) {
    int height = static_cast<int>(mat.size());
    if (height == 0) return 0;
    int width = static_cast<int>(mat[0].size());
    if (width == 0) return 0;

    int row_bytes = width * 3;
    int padding = (4 - (row_bytes % 4)) % 4;
    int stride = row_bytes + padding;
    uint32_t image_size = static_cast<uint32_t>(stride * height);
    uint32_t file_size = 54 + image_size;

    std::ofstream out(path, std::ios::binary);
    if (!out.is_open()) return 0;

    uint8_t file_header[14] = {
        'B', 'M',
        static_cast<uint8_t>(file_size & 0xFF),
        static_cast<uint8_t>((file_size >> 8) & 0xFF),
        static_cast<uint8_t>((file_size >> 16) & 0xFF),
        static_cast<uint8_t>((file_size >> 24) & 0xFF),
        0, 0, 0, 0,
        54, 0, 0, 0
    };
    out.write(reinterpret_cast<const char*>(file_header), 14);

    uint8_t info_header[40] = {0};
    info_header[0] = 40;
    info_header[4] = static_cast<uint8_t>(width & 0xFF);
    info_header[5] = static_cast<uint8_t>((width >> 8) & 0xFF);
    info_header[6] = static_cast<uint8_t>((width >> 16) & 0xFF);
    info_header[7] = static_cast<uint8_t>((width >> 24) & 0xFF);

    info_header[8] = static_cast<uint8_t>(height & 0xFF);
    info_header[9] = static_cast<uint8_t>((height >> 8) & 0xFF);
    info_header[10] = static_cast<uint8_t>((height >> 16) & 0xFF);
    info_header[11] = static_cast<uint8_t>((height >> 24) & 0xFF);

    info_header[12] = 1;
    info_header[14] = 24;

    info_header[20] = static_cast<uint8_t>(image_size & 0xFF);
    info_header[21] = static_cast<uint8_t>((image_size >> 8) & 0xFF);
    info_header[22] = static_cast<uint8_t>((image_size >> 16) & 0xFF);
    info_header[23] = static_cast<uint8_t>((image_size >> 24) & 0xFF);

    out.write(reinterpret_cast<const char*>(info_header), 40);

    uint8_t pad_bytes[3] = {0, 0, 0};
    for (int y = height - 1; y >= 0; --y) {
        for (int x = 0; x < width; ++x) {
            uint8_t r = 0, g = 0, b = 0;
            if constexpr (std::is_same_v<T, std::string>) {
                const std::string& val = mat[y][x];
                if (val == "navy") {
                    r = 0; g = 0; b = 128;
                } else if (val == "white" || val == "#") {
                    r = 255; g = 255; b = 255;
                } else if (val == "black" || val == " ") {
                    r = 0; g = 0; b = 0;
                } else if (val == "red") {
                    r = 255; g = 0; b = 0;
                } else if (val == "green") {
                    r = 0; g = 255; b = 0;
                } else if (val == "blue") {
                    r = 0; g = 0; b = 255;
                } else if (val == "yellow") {
                    r = 255; g = 255; b = 0;
                } else {
                    r = 255; g = 255; b = 255;
                }
            } else {
                double d = static_cast<double>(mat[y][x]);
                if (d > 255.0) d = 255.0;
                if (d < 0.0) d = 0.0;
                uint8_t gray = static_cast<uint8_t>(d);
                r = gray; g = gray; b = gray;
            }
            uint8_t pixel[3] = {b, g, r};
            out.write(reinterpret_cast<const char*>(pixel), 3);
        }
        if (padding > 0) {
            out.write(reinterpret_cast<const char*>(pad_bytes), padding);
        }
    }
    out.close();
    return 1;
}

// Helper nativo para delegar a abertura de arquivo para o aplicativo padrao do SO
inline int __minipar_launch_file(const std::string& path) {
#ifdef _WIN32
    std::string win_path = path;
    for (char& c : win_path) {
        if (c == '/') c = '\\\\';
    }
    HINSTANCE res = ShellExecuteA(NULL, "open", win_path.c_str(), NULL, NULL, SW_SHOWNORMAL);
    return (reinterpret_cast<INT_PTR>(res) > 32) ? 1 : 0;
#elif defined(__linux__)
    int res = system(("xdg-open \\\"" + path + "\\\" &").c_str());
    return (res == 0) ? 1 : 0;
#else
    return 0;
#endif
}

// Helper nativo para gravacao atomica de arquivos de texto em disco
inline int __minipar_write_file(const std::string& path, const std::string& content) {
    try {
        std::filesystem::path p(path);
        if (p.has_parent_path()) {
            std::filesystem::create_directories(p.parent_path());
        }
        std::ofstream out(p);
        if (!out.is_open()) return 0;
        out << content;
        out.close();
        return 1;
    } catch (...) {
        return 0;
    }
}


// Helper para Input
std::string input() {
    std::string s;
    std::getline(std::cin, s);
    return s;
}

std::string input(const std::string& prompt) {
    std::cout << prompt;
    return input();
}

// Converte linha com inteiros separados por espaco em vetor (ex.: "10 -3 80")
std::vector<double> __parse_ints(const std::string& s) {
    std::vector<double> result;
    std::istringstream iss(s);
    double n;
    while (iss >> n) {
        result.push_back(n);
    }
    return result;
}

std::vector<int> __minipar_range(int end) {
    std::vector<int> values;
    for (int i = 0; i < end; ++i) values.push_back(i);
    return values;
}

std::vector<int> __minipar_range(int start, int end) {
    std::vector<int> values;
    for (int i = start; i < end; ++i) values.push_back(i);
    return values;
}

// Helper para Arrays (.pop) do Python
template<typename T>
auto __array_pop(std::vector<T>& v) {
    if (v.empty()) return T{};
    auto val = v.back();
    v.pop_back();
    return val;
}

// Helper para formatar e printar std::vector (arrays e matrizes) nativamente
template <typename T>
std::ostream& operator<<(std::ostream& os, const std::vector<T>& v) {
    os << "[";
    for (size_t i = 0; i < v.size(); ++i) {
        os << v[i];
        if (i != v.size() - 1) os << ", ";
    }
    os << "]";
    return os;
}

template<typename T>
std::string __to_string(const T& val) {
    if constexpr (std::is_constructible_v<std::string, T>) {
        return std::string(val);
    } else {
        return std::to_string(val);
    }
}

// Índices são inteiros não negativos; strings usam bytes, adequados ao lexer ASCII.
size_t __checked_index(double index) {
    if (!std::isfinite(index) || index < 0 || std::floor(index) != index ||
        index >= static_cast<double>(std::numeric_limits<size_t>::max())) {
        throw std::out_of_range("Indice deve ser inteiro nao negativo");
    }
    return static_cast<size_t>(index);
}

std::string __index(const std::string& text, double index) {
    return std::string(1, text.at(__checked_index(index)));
}

template<typename T>
const T& __index(const std::vector<T>& values, double index) {
    return values.at(__checked_index(index));
}

template<typename T>
T& __index(std::vector<T>& values, double index) {
    return values.at(__checked_index(index));
}

template<typename T, typename V>
void __set_index(std::vector<T>& values, double index, const V& value) {
    values.at(__checked_index(index)) = value;
}

void __set_index(std::string& text, double index, const std::string& value) {
    if (value.size() != 1) throw std::invalid_argument("Atribuicao por indice exige um byte");
    text.at(__checked_index(index)) = value[0];
}

template<typename... Args>
auto __make_list(const Args&... values) {
    if constexpr (sizeof...(Args) > 0 && (std::is_same_v<Args, std::string> && ...)) {
        return std::vector<std::string>{values...};
    } else {
        static_assert((std::is_arithmetic_v<Args> && ...), "Lista exige elementos numericos ou strings homogeneas");
        return std::vector<double>{static_cast<double>(values)...};
    }
}

int __checked_int(double number) {
    if (!std::isfinite(number) || std::trunc(number) < std::numeric_limits<int>::min() ||
        std::trunc(number) > std::numeric_limits<int>::max()) {
        throw std::out_of_range("Valor fora da faixa de int");
    }
    return static_cast<int>(number);
}

int __to_int(const std::string& value) {
    return __checked_int(std::stod(value));
}

template<typename T>
int __to_int(T value) {
    return __checked_int(static_cast<double>(value));
}

template<typename T>
auto __make_matrix(int rows, int cols, T init_val) {
    using ActualT = std::conditional_t<std::is_same_v<std::decay_t<T>, const char*>, std::string, T>;
    return std::vector<std::vector<ActualT>>(rows, std::vector<ActualT>(cols, init_val));
}

class MiniParChannel {
public:
    std::string ip;
    int port;

    MiniParChannel(std::string ip, int port) : ip(ip), port(port) {}

    void sendData(std::string msg) {
        struct sockaddr_in serv_addr;
        memset(&serv_addr, 0, sizeof(serv_addr));
        serv_addr.sin_family = AF_INET;
        serv_addr.sin_port = htons(port);
        inet_pton(AF_INET, ip.c_str(), &serv_addr.sin_addr);
        
        for (int i = 0; i < 50; i++) {
            int sock = socket(AF_INET, SOCK_STREAM, 0);
            if (sock >= 0) {
                if (connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) >= 0) {
                    send(sock, msg.c_str(), msg.length(), 0);
                    #ifdef _WIN32
                    shutdown(sock, SD_SEND);
                    #else
                    shutdown(sock, SHUT_WR);
                    #endif
                    char ack[16];
                    recv(sock, ack, sizeof(ack), 0);
                    CLOSE_SOCK(sock);
                    return;
                }
                CLOSE_SOCK(sock);
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }

    std::string receiveData() {
        int server_fd = -1;
        int opt = 1;
        struct sockaddr_in address;
        memset(&address, 0, sizeof(address));
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = INADDR_ANY;
        address.sin_port = htons(port);

        for (int i = 0; i < 30; i++) {
            server_fd = socket(AF_INET, SOCK_STREAM, 0);
            if (server_fd >= 0) {
                setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
                if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) >= 0) {
                    break;
                }
                CLOSE_SOCK(server_fd);
                server_fd = -1;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
        if (server_fd < 0) return "";
        if (listen(server_fd, 3) < 0) { CLOSE_SOCK(server_fd); return ""; }
        
        int new_socket = accept(server_fd, nullptr, nullptr);
        if (new_socket < 0) { CLOSE_SOCK(server_fd); return ""; }
        
        char buffer[4096] = {0};
        int bytes = recv(new_socket, buffer, 4096, 0);
        std::string result(buffer, bytes > 0 ? bytes : 0);
        send(new_socket, "OK", 2, 0);
        
        CLOSE_SOCK(new_socket);
        CLOSE_SOCK(server_fd);
        return result;
    }
};

"""
