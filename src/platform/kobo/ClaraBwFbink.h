#pragma once
// CP-KOBO-018: FBInk image handoff for Clara BW Variant A.
// Dry-run output only unless explicitly opted in. No Nickel process control.
// A generated PNM frame is never evidence of E Ink hardware compatibility.
#include "ClaraBwPlatform.h"
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

namespace crosspoint::kobo {
class FbinkPnmSink final : public DisplaySink {
public:
    explicit FbinkPnmSink(std::string outputPath, bool allowDisplay=false, std::string fbinkPath="/usr/bin/fbink")
        : output_(std::move(outputPath)), enabled_(allowDisplay), fbink_(std::move(fbinkPath)) {}
    bool present(const PanelGray8& frame) override {
        if (!frame.pixels || frame.width!=kPanelWidth || frame.height!=kPanelHeight ||
            frame.length<static_cast<size_t>(kPanelWidth)*kPanelHeight || output_.empty()) return false;
        // PNM P5 is supported by FBInk's image loader. Write atomically, in
        // the SAME directory, so FBInk cannot read a partially written frame.
        const std::string temporary=output_+".tmp";
        {
            std::ofstream file(temporary,std::ios::binary|std::ios::trunc);
            if (!file) return false;
            file << "P5\n" << kPanelWidth << " " << kPanelHeight << "\n255\n";
            file.write(reinterpret_cast<const char*>(frame.pixels),
                       static_cast<std::streamsize>(static_cast<size_t>(kPanelWidth)*kPanelHeight));
            file.flush();
            if (!file) return false;
        }
        if (std::rename(temporary.c_str(),output_.c_str())!=0) return false;
        ++presentCount;
        if (!enabled_) return true; // Dry run: NO process exec or hardware writes.
        // Avoid a shell entirely; no string expansion, redirection, or injection.
        const pid_t pid=fork();
        if (pid<0) return false;
        if (pid==0) {
            execl(fbink_.c_str(),fbink_.c_str(),"-W","AUTO","-i",output_.c_str(),static_cast<char*>(nullptr));
            _exit(127);
        }
        int status=0;
        if (waitpid(pid,&status,0)!=pid) return false;
        return WIFEXITED(status) && WEXITSTATUS(status)==0;
    }
    unsigned presentCount=0;
private:
    std::string output_;
    bool enabled_;
    std::string fbink_;
};
} // namespace crosspoint::kobo
