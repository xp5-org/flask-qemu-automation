// bus_bridge.hpp -- generic synchronous bus-transaction bridge for embedding
// a Verilated model into a host process 
#pragma once

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <mutex>
#include <queue>
#include <thread>

namespace busbridge {

// Mirrors one Nova IOT transaction to device 042 -- see verilator_vga's
// __testlist__vga_hello_live.py scope discussion for why the bus shape
// follows Nova's DOA/DOB/DOC/DIA/DIB/DIC + S/C/P pulse field directly rather
// than inventing a new register scheme: it's what lets the RTL's
// Nova-visible programming model stay byte-identical to the C model it
// replaces.
struct Transaction {
    uint8_t reg_sel = 0;   // 0=A 1=B 2=C
    bool we = false;        // true = DO* (write), false = DI* (read)
    uint8_t pulse = 0;      // 0=none 1=S 2=C 3=P
    uint16_t data_in = 0;
    uint16_t data_out = 0;  // filled in by the clock thread
    bool done = false;
};

// Dut: whatever Verilated top-module type. Caller supplies:
//   apply(dut, txn)   drive bus inputs from txn, pulse the bus clock once,
//                     capture data_out -- exactly one register transaction
//   tick(dut)          advance the free-running domain by one clock edge
//
// No real-time pacing: a design small enough to need this (a display
// controller, not a CPU) evaluates far faster than its own nominal clock
// rate under Verilator, so the thread just runs flat out. That is enough to
// make "real ~25MHz timing constants" (the actual VESA/VGA numbers, not
// scaled-down placeholders) meaningful without fighting OS sleep
// granularity at tens of nanoseconds.
template <typename Dut>
class ClockThread {
public:
    using ApplyFn = std::function<void(Dut &, Transaction &)>;
    using TickFn = std::function<void(Dut &)>;

    ClockThread(Dut &dut, ApplyFn apply, TickFn tick)
        : dut_(dut), apply_(std::move(apply)), tick_(std::move(tick)) {}

    ~ClockThread() { stop(); }

    void start() {
        if (running_) return;
        running_ = true;
        thread_ = std::thread(&ClockThread::run, this);
    }

    void stop() {
        if (!running_) return;
        running_ = false;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            cv_.notify_all();
        }
        if (thread_.joinable()) thread_.join();
    }

    // Blocking call from ANY thread other than the clock thread itself.
    uint16_t submit(uint8_t reg_sel, bool we, uint8_t pulse, uint16_t data_in) {
        Transaction txn;
        txn.reg_sel = reg_sel;
        txn.we = we;
        txn.pulse = pulse;
        txn.data_in = data_in;
        {
            std::unique_lock<std::mutex> lock(mutex_);
            pending_.push(&txn);
            cv_.notify_all();
            cv_.wait(lock, [&] { return txn.done; });
        }
        return txn.data_out;
    }

    bool is_running() const { return running_; }

private:
    void run() {
        while (running_) {
            std::unique_lock<std::mutex> lock(mutex_);
            // Drain pending transactions before the next pixel tick, so a
            // register write is visible to scanout logic in the same order
            // a synchronous C call would have guaranteed.
            while (!pending_.empty()) {
                Transaction *txn = pending_.front();
                pending_.pop();
                lock.unlock();
                apply_(dut_, *txn);
                lock.lock();
                txn->done = true;
            }
            cv_.notify_all();
            lock.unlock();

            tick_(dut_);
        }
    }

    Dut &dut_;
    ApplyFn apply_;
    TickFn tick_;
    std::atomic<bool> running_{false};
    std::thread thread_;
    std::mutex mutex_;
    std::condition_variable cv_;
    std::queue<Transaction *> pending_;
};

}  // namespace busbridge
