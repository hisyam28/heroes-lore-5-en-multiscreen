#ifndef HL5_GUEST_HEAP_H
#define HL5_GUEST_HEAP_H
#include <stdint.h>

namespace hl5 {
// Host-side allocation metadata. Guest addresses/data layouts are unchanged.
// Metadata uses a bounded pool so free/coalescing never allocates host memory.
template<uint32_t MaxNodes = 65536> class GuestHeap {
    static constexpr uint32_t nil = 0xffffffffu;
    struct Node { uint32_t start, size, requested, previous, next; };
    Node nodes_[MaxNodes];
    uint32_t base_ = 0, capacity_ = 0, created_ = 0, recycled_ = nil;
    uint32_t used_ = 0, peak_ = 0, live_ = 0;
    uint32_t cursor_ = 0;
    uint32_t acquire() {
        if (recycled_ != nil) { uint32_t i = recycled_; recycled_ = nodes_[i].next; return i; }
        return created_ < MaxNodes ? created_++ : nil;
    }
    void recycle(uint32_t index) { nodes_[index].next = recycled_; recycled_ = index; }
    uint32_t find(uint32_t address) const {
        for (uint32_t i = 0; i != nil; i = nodes_[i].next) {
            if (nodes_[i].start == address) return i;
            if (nodes_[i].start > address) break;
        }
        return nil;
    }
    void insert_after(uint32_t previous, uint32_t index, uint32_t start, uint32_t size, uint32_t requested) {
        uint32_t next = nodes_[previous].next;
        nodes_[index] = {start, size, requested, previous, next};
        nodes_[previous].next = index;
        if (next != nil) nodes_[next].previous = index;
    }
    void join_next(uint32_t index) {
        uint32_t next = nodes_[index].next;
        nodes_[index].size += nodes_[next].size;
        nodes_[index].next = nodes_[next].next;
        if (nodes_[index].next != nil) nodes_[nodes_[index].next].previous = index;
        recycle(next);
    }
    static uint32_t rounded(uint32_t size) {
        uint64_t result = (uint64_t(size ? size : 1) + 7) & ~uint64_t(7);
        return result <= 0xffffffffULL ? static_cast<uint32_t>(result) : 0;
    }
public:
    void reset(uint32_t base, uint32_t capacity) {
        base_ = base; capacity_ = capacity; created_ = 1; recycled_ = nil;
        used_ = peak_ = live_ = 0; cursor_ = 0;
        nodes_[0] = {base, capacity, 0, nil, nil};
    }
    uint32_t allocate(uint32_t size, uint32_t alignment = 8) {
        if (!capacity_ || !alignment || (alignment & (alignment - 1))) return 0;
        uint32_t count = rounded(size);
        if (!count || count > capacity_) return 0;
        for (uint32_t i = cursor_, scanned = 0; scanned < created_; ++scanned,
             i = nodes_[i].next == nil ? 0 : nodes_[i].next) {
            if (nodes_[i].requested) continue;
            uint64_t aligned = (uint64_t(nodes_[i].start) + alignment - 1) & ~uint64_t(alignment - 1);
            uint64_t end = uint64_t(nodes_[i].start) + nodes_[i].size;
            if (aligned + count > end) continue;
            uint32_t prefix = static_cast<uint32_t>(aligned - nodes_[i].start);
            uint32_t suffix = static_cast<uint32_t>(end - aligned - count);
            uint32_t first = nil, second = nil;
            if (prefix || suffix) { first = acquire(); if (first == nil) return 0; }
            if (prefix && suffix) {
                second = acquire();
                if (second == nil) { recycle(first); return 0; }
            }
            uint32_t allocation = i;
            if (prefix) {
                nodes_[i].size = prefix;
                insert_after(i, first, static_cast<uint32_t>(aligned), count, size ? size : 1);
                allocation = first;
                if (suffix) insert_after(first, second, static_cast<uint32_t>(aligned) + count, suffix, 0);
            } else {
                nodes_[i].size = count; nodes_[i].requested = size ? size : 1;
                if (suffix) insert_after(i, first, nodes_[i].start + count, suffix, 0);
            }
            used_ += count; ++live_; if (used_ > peak_) peak_ = used_;
            cursor_ = nodes_[allocation].next == nil ? 0 : nodes_[allocation].next;
            return nodes_[allocation].start;
        }
        return 0;
    }
    bool release(uint32_t address) {
        if (!address) return true;
        uint32_t i = find(address);
        if (i == nil || !nodes_[i].requested) return false;
        used_ -= nodes_[i].size; --live_; nodes_[i].requested = 0;
        uint32_t previous = nodes_[i].previous;
        if (previous != nil && !nodes_[previous].requested) { join_next(previous); i = previous; }
        if (nodes_[i].next != nil && !nodes_[nodes_[i].next].requested) join_next(i);
        cursor_ = i;
        return true;
    }
    bool owns(uint32_t address) const {
        uint32_t i = find(address); return i != nil && nodes_[i].requested;
    }
    uint32_t requested_size(uint32_t address) const {
        uint32_t i = find(address); return i != nil ? nodes_[i].requested : 0;
    }
    bool resize_in_place(uint32_t address, uint32_t size) {
        uint32_t i = find(address), count = rounded(size);
        if (i == nil || !nodes_[i].requested || !size || !count || count > capacity_) return false;
        uint32_t old = nodes_[i].size, next = nodes_[i].next;
        if (count > old) {
            uint32_t delta = count - old;
            if (next == nil || nodes_[next].requested || nodes_[next].size < delta) return false;
            if (nodes_[next].size == delta) join_next(i);
            else { nodes_[next].start += delta; nodes_[next].size -= delta; nodes_[i].size = count; }
            used_ += delta; if (used_ > peak_) peak_ = used_;
        } else if (count < old) {
            uint32_t tail = old - count;
            if (next != nil && !nodes_[next].requested) {
                nodes_[next].start -= tail; nodes_[next].size += tail;
            } else {
                uint32_t index = acquire();
                if (index == nil) { nodes_[i].requested = size; return true; }
                insert_after(i, index, address + count, tail, 0);
            }
            nodes_[i].size = count; used_ -= tail;
        }
        nodes_[i].requested = size;
        cursor_ = nodes_[i].next == nil ? 0 : nodes_[i].next;
        return true;
    }
    uint32_t in_use() const { return used_; }
    uint32_t available() const { return capacity_ - used_; }
    uint32_t peak() const { return peak_; }
    uint32_t live_allocations() const { return live_; }
    uint32_t largest_free() const {
        uint32_t largest = 0;
        for (uint32_t i = 0; i != nil; i = nodes_[i].next)
            if (!nodes_[i].requested && nodes_[i].size > largest) largest = nodes_[i].size;
        return largest;
    }
    bool validate() const {
        uint64_t position = base_; uint32_t previous = nil, count = 0, used = 0, live = 0;
        bool cursor_seen = false;
        for (uint32_t i = 0; i != nil; i = nodes_[i].next) {
            if (i >= created_ || ++count > MaxNodes) return false;
            const auto& node = nodes_[i];
            if (i == cursor_) cursor_seen = true;
            if (!node.size || node.start != position || node.previous != previous || node.requested > node.size) return false;
            if (node.requested) { used += node.size; ++live; }
            else if (previous != nil && !nodes_[previous].requested) return false;
            position += node.size; previous = i;
        }
        return cursor_seen && position == uint64_t(base_) + capacity_ && used == used_ && live == live_;
    }
};
}
#endif
