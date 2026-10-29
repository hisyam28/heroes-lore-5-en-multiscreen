#pragma once
namespace hl5 {
// Bounded tracking: a full table falls back to the old immediate sync.
class SaveCommitTracker {
    int descriptors_[64] = {};
public:
    bool mark(int fd) {
        if (fd<=2) return false;
        for (int value:descriptors_) if (value==fd) return true;
        for (int& value:descriptors_) if (!value) { value=fd; return true; }
        return false;
    }
    bool dirty(int fd) const {
        if (fd<=2) return false;
        for (int value:descriptors_) if (value==fd) return true;
        return false;
    }
    void clear(int fd) { for (int& value:descriptors_) if (value==fd) value=0; }
};
// Always close, including on sync failure. Report a failed durability fence
// to the guest rather than claiming that the save was committed.
template<class Sync,class Close>
static inline int commit_save_close(SaveCommitTracker& tracker,int fd,Sync sync,Close close) {
    int synced=tracker.dirty(fd)?sync(fd):0;
    int closed=close(fd);tracker.clear(fd);
    return synced<0?-1:closed;
}
}
