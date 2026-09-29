import numpy as np
import sounddevice as sd
import scipy.signal as signal
import matplotlib.pyplot as plt
import time
import os

def generate_chirp(duration, fs, f0, f1):
    """Generate a linear frequency sweep (Chirp) for RIR measurement."""
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    sweep = signal.chirp(t, f0, duration, f1, method='linear')
    
    # 5% fade in/out to avoid clicks
    fade_len = int(fs * duration * 0.05)
    window = np.ones_like(sweep)
    if fade_len > 0:
        window[:fade_len] = np.linspace(0, 1, fade_len)
        window[-fade_len:] = np.linspace(1, 0, fade_len)
    
    return sweep * window

def extract_rir(recorded, source, fs):
    """
    Extract Room Impulse Response using matched filter (cross-correlation).
    Returns the aligned RIR and corresponding time array.
    """
    # Cross-correlate recorded signal with the original source (chirp)
    # This acts as a matched filter and compresses the chirp into an impulse
    rir = signal.correlate(recorded, source, mode='full')
    
    # The peak of the correlation corresponds to the direct sound (assuming no latency).
    # However, sounddevice playrec might have an unknown hardware/software latency.
    # We will align the direct sound (the maximum peak) to time = 0.
    max_idx = np.argmax(np.abs(rir))
    
    # Take the portion of the RIR after the direct sound
    rir_causal = rir[max_idx:]
    t = np.linspace(0, len(rir_causal)/fs, len(rir_causal))
    
    # Normalize for better visualization
    rir_causal = rir_causal / np.max(np.abs(rir_causal))
    
    return t, rir_causal

def measure_rir():
    print("=" * 50)
    print(" EchoMap E1 & E2: RIR Extraction")
    print("=" * 50)
    
    # Configuration
    fs = 48000
    # Use 4kHz ~ 12kHz based on the calibration result (cuts off sharply at 14kHz)
    f0 = 4000
    f1 = 12000
    chirp_duration = 0.1 # 100ms short chirp
    recording_duration = 0.5 # Record for 500ms to catch the reverb
    
    print(f"Generating {chirp_duration*1000}ms chirp from {f0}Hz to {f1}Hz...")
    chirp_sig = generate_chirp(chirp_duration, fs, f0, f1)
    
    # Pad the playback signal so it plays silence while continuing to record
    playback_sig = np.pad(chirp_sig, (0, int(fs * (recording_duration - chirp_duration))))
    
    print("\n[READY] Please place your laptop facing a wall (about 1~2 meters away).")
    input("Press Enter to start measurement...")
    
    print("\n--> Playing & Recording...")
    # Blocking play & record
    recorded = sd.playrec(playback_sig, samplerate=fs, channels=1, blocking=True)
    recorded = recorded.flatten()
    print("Done recording!")
    
    print("\nExtracting RIR...")
    t, rir = extract_rir(recorded, chirp_sig, fs)
    
    # Convert time to distance (round trip)
    # distance = speed_of_sound * time / 2
    # speed of sound approx 343 m/s
    speed_of_sound = 343.0
    distance = (t * speed_of_sound) / 2
    
    # Plotting
    plt.figure(figsize=(12, 6))
    
    # Focus on the first 15 meters
    valid_idx = distance <= 15.0
    dist_plot = distance[valid_idx]
    rir_plot = np.abs(rir[valid_idx])
    
    plt.plot(dist_plot, rir_plot, color='blue')
    plt.title("Room Impulse Response (Envelope)")
    plt.xlabel("Distance [m]")
    plt.ylabel("Normalized Amplitude")
    plt.grid(True)
    
    # Find peaks to suggest reflections
    # distance 0 is direct sound, skip it
    peaks, _ = signal.find_peaks(rir_plot, height=0.1, distance=int(0.1 / (speed_of_sound / fs / 2))) 
    # exclude direct sound peak (near 0)
    peaks = peaks[dist_plot[peaks] > 0.3] 
    
    for p in peaks:
        plt.plot(dist_plot[p], rir_plot[p], "rx")
        plt.text(dist_plot[p], rir_plot[p] + 0.05, f"{dist_plot[p]:.2f}m", color='red')
        
    plt.tight_layout()
    output_filename = "rir_result.png"
    plt.savefig(output_filename)
    print(f"\nSaved RIR plot to {output_filename}")
    print("Check the image to see if a peak corresponds to the wall's distance!")

if __name__ == "__main__":
    measure_rir()
