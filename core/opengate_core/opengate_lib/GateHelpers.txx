/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

// color list
// https://github.com/fmtlib/fmt/blob/master/include/fmt/color.h

// FIXME to put elsewhere, only when Log is required

template<typename S, typename... Args>
void Log(int level, const S &format_str, Args &&... args) {
    if (level > GateSourceManager::fVerboseLevel) return;
    fmt::print(fg(fmt::color::bisque), format_str, args...);
}


template<typename S, typename... Args>
void LogDebug(const S &format_str, Args &&... args) {
    fmt::print(fg(fmt::color::crimson), format_str, args...);
}
