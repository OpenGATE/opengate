#ifndef OPENGATE_EXTERNAL_UTILITY_CT_FUNCTIONARITY_H
#define OPENGATE_EXTERNAL_UTILITY_CT_FUNCTIONARITY_H

namespace ct {

template<typename F> struct FunctionArity;
template<typename Return, typename... Args>
struct FunctionArity<Return (*)(Args...)> {
    static constexpr unsigned value = sizeof...(Args);
};
template<typename C, typename Return, typename... Args>
struct FunctionArity<Return (C::*)(Args...)> {
    static constexpr unsigned value = sizeof...(Args);
};
template<typename C, typename Return, typename... Args>
struct FunctionArity<Return (C::*)(Args...) const> {
    static constexpr unsigned value = sizeof...(Args);
};
template<typename C, typename Return, typename... Args>
struct FunctionArity<Return (C::*)(Args...) volatile> {
    static constexpr unsigned value = sizeof...(Args);
};
template<typename C, typename Return, typename... Args>
struct FunctionArity<Return (C::*)(Args...) const volatile> {
    static constexpr unsigned value = sizeof...(Args);
};
template<typename C, typename Return, typename... Args>
struct FunctionArity<Return (C::*)(Args...)&> {
    static constexpr unsigned value = sizeof...(Args);
};
template<typename C, typename Return, typename... Args>
struct FunctionArity<Return (C::*)(Args...) const &> {
    static constexpr unsigned value = sizeof...(Args);
};
template<typename C, typename Return, typename... Args>
struct FunctionArity<Return (C::*)(Args...) volatile &> {
    static constexpr unsigned value = sizeof...(Args);
};
template<typename C, typename Return, typename... Args>
struct FunctionArity<Return (C::*)(Args...) const volatile &> {
    static constexpr unsigned value = sizeof...(Args);
};
template<typename C, typename Return, typename... Args>
struct FunctionArity<Return (C::*)(Args...)&&> {
    static constexpr unsigned value = sizeof...(Args);
};
template<typename C, typename Return, typename... Args>
struct FunctionArity<Return (C::*)(Args...) const &&> {
    static constexpr unsigned value = sizeof...(Args);
};
template<typename C, typename Return, typename... Args>
struct FunctionArity<Return (C::*)(Args...) volatile &&> {
    static constexpr unsigned value = sizeof...(Args);
};
template<typename C, typename Return, typename... Args>
struct FunctionArity<Return (C::*)(Args...) const volatile &&> {
    static constexpr unsigned value = sizeof...(Args);
};

template<typename F>
constexpr auto functionArity(F) {
    return FunctionArity<F>::value;
}

}

#endif
