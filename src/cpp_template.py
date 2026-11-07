_CPP_HEADER = """\
#include <iostream>
#include <string>
#include <sstream>
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

#ifdef _WIN32
  #ifndef NOMINMAX
    #define NOMINMAX
  #endif
  #include <winsock2.h>
  #include <ws2tcpip.h>
  #include <windows.h>
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
void __set_core_affinity(int core_id) {
    if (core_id < 0) return;
#ifdef _WIN32
    DWORD_PTR mask = (static_cast<DWORD_PTR>(1) << (core_id % 64));
    SetThreadAffinityMask(GetCurrentThread(), mask);
#elif defined(__linux__)
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(core_id, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
#endif
}

// Pool global e thread-safe de tarefas disparadas por fork para sincronizacao com barreira (join;)
inline std::mutex __task_pool_mtx;
inline std::vector<std::function<void()>> __task_pool;

template<typename T>
std::shared_future<T> __register_task(std::future<T> fut) {
    auto sf = fut.share();
    {
        std::lock_guard<std::mutex> lock(__task_pool_mtx);
        __task_pool.push_back([sf]() mutable {
            if (sf.valid()) sf.wait();
        });
    }
    return sf;
}

template<typename T>
std::shared_future<T> __register_task(std::shared_future<T> sf) {
    {
        std::lock_guard<std::mutex> lock(__task_pool_mtx);
        __task_pool.push_back([sf]() mutable {
            if (sf.valid()) sf.wait();
        });
    }
    return sf;
}

inline void __task_pool_wait_all() {
    std::vector<std::function<void()>> tasks;
    {
        std::lock_guard<std::mutex> lock(__task_pool_mtx);
        tasks = std::move(__task_pool);
        __task_pool.clear();
    }
    for (auto& task : tasks) {
        if (task) task();
    }
}

// Helper para sincronizacao de tarefas com argumentos join(t) ou join(lista_de_tarefas)
template<typename T>
void __minipar_join_target(std::future<T>& f) {
    if (f.valid()) f.wait();
}

template<typename T>
void __minipar_join_target(std::shared_future<T>& f) {
    if (f.valid()) f.wait();
}

template<typename T>
void __minipar_join_target(const std::shared_future<T>& f) {
    if (f.valid()) f.wait();
}

template<typename T>
void __minipar_join_target(std::vector<T>& vec) {
    for (auto& item : vec) {
        __minipar_join_target(item);
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
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) return;
        struct sockaddr_in serv_addr;
        serv_addr.sin_family = AF_INET;
        serv_addr.sin_port = htons(port);
        inet_pton(AF_INET, ip.c_str(), &serv_addr.sin_addr);
        
        for(int i=0; i<50; i++) {
            if (connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) >= 0) {
                send(sock, msg.c_str(), msg.length(), 0);
                break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        CLOSE_SOCK(sock);
    }

    std::string receiveData() {
        int server_fd = socket(AF_INET, SOCK_STREAM, 0);
        if (server_fd < 0) return "";
        int opt = 1;
        setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
        
        struct sockaddr_in address;
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = INADDR_ANY;
        address.sin_port = htons(port);
        
        if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) { CLOSE_SOCK(server_fd); return ""; }
        if (listen(server_fd, 3) < 0) { CLOSE_SOCK(server_fd); return ""; }
        
        int new_socket = accept(server_fd, nullptr, nullptr);
        if (new_socket < 0) { CLOSE_SOCK(server_fd); return ""; }
        
        char buffer[4096] = {0};
        recv(new_socket, buffer, 4096, 0);
        std::string result(buffer);
        
        CLOSE_SOCK(new_socket);
        CLOSE_SOCK(server_fd);
        return result;
    }
};

"""
