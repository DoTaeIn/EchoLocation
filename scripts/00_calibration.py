import numpy as np
import sounddevice as sd
import scipy.signal as signal
import matplotlib.pyplot as plt
import time

def generate_sweep(duration, fs, f0, f1, method='logarithmic'):
    """Generate a frequency sweep."""
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    sweep = signal.chirp(t, f0, duration, f1, method=method)
    
    # Apply fade in/out to avoid clicks
    fade_len = int(fs * 0.05) # 50ms fade
    window = np.ones_like(sweep)
    window[:fade_len] = np.linspace(0, 1, fade_len)
    window[-fade_len:] = np.linspace(1, 0, fade_len)
    
    return sweep * window

def calibrate_audio(fs=48000, duration=2.0, f0=100, f1=24000):
    print("=" * 50)
    print(" EchoMap E0: Audio I/O Calibration")
    print("=" * 50)
    
    print(f"Generating frequency sweep from {f0} Hz to {f1} Hz over {duration} seconds...")
    sweep = generate_sweep(duration, fs, f0, f1)
    
    print("\n[IMPORTANT] Playing and recording in 3 seconds...")
    print("Make sure your laptop speakers are unmuted and the volume is up.")
    print("macOS might ask for Microphone permissions. Please allow it.")
    for i in range(3, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)
        
    print("\n--> Playing & Recording... Please wait.")
    
    # sounddevice playrec
    # Play the sweep and record simultaneously.
    # We record slightly longer to catch reverb if any, but for calibration, exactly duration is okay.
    recorded = sd.playrec(sweep, samplerate=fs, channels=1, blocking=True)
    recorded = recorded.flatten()
    
    print("Done recording!")
    
    # Analyze the frequency response using Welch's method for Power Spectral Density
    print("\nAnalyzing frequency response...")
    f, Pxx_den = signal.welch(recorded, fs, nperseg=4096)
    
    # Plotting
    plt.figure(figsize=(12, 8))
    
    # 1. Plot the time-domain recorded signal
    plt.subplot(2, 1, 1)
    t = np.linspace(0, len(recorded)/fs, len(recorded))
    plt.plot(t, recorded, color='blue', alpha=0.7)
    plt.title("Recorded Signal (Time Domain)")
    plt.xlabel("Time [s]")
    plt.ylabel("Amplitude")
    plt.grid(True)
    
    # 2. Plot the Frequency Response
    plt.subplot(2, 1, 2)
    plt.semilogy(f, Pxx_den, color='red')
    plt.title("Frequency Response (Power Spectral Density)")
    plt.xlabel("Frequency [Hz]")
    plt.ylabel("PSD [V**2/Hz]")
    plt.xlim([0, fs/2])
    plt.grid(True, which="both", ls="-", alpha=0.2)
    
    # Highlight the near-inaudible band (17kHz - 22kHz)
    plt.axvspan(17000, 22000, color='green', alpha=0.2, label="Target High-Freq Band (17-22 kHz)")
    plt.legend()
    
    plt.tight_layout()
    output_filename = "calibration_result.png"
    plt.savefig(output_filename)
    print(f"\nSaved calibration plot to {output_filename}")
    print("Open this image to check if your speaker/mic combo captures the green target band properly.")

if __name__ == "__main__":
    calibrate_audio()
