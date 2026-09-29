import numpy as np
import sounddevice as sd
import scipy.signal as signal
import matplotlib.pyplot as plt
import time
import os

def generate_chirp(duration, fs, f0, f1):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    sweep = signal.chirp(t, f0, duration, f1, method='linear')
    fade_len = int(fs * duration * 0.05)
    window = np.ones_like(sweep)
    if fade_len > 0:
        window[:fade_len] = np.linspace(0, 1, fade_len)
        window[-fade_len:] = np.linspace(1, 0, fade_len)
    return sweep * window

def extract_rir_peaks(recorded, source, fs, speed_of_sound=343.0):
    rir = signal.correlate(recorded, source, mode='full')
    max_idx = np.argmax(np.abs(rir))
    rir_causal = rir[max_idx:]
    t = np.linspace(0, len(rir_causal)/fs, len(rir_causal))
    rir_causal = rir_causal / np.max(np.abs(rir_causal))
    
    distance = (t * speed_of_sound) / 2
    valid_idx = distance <= 10.0 # Only look up to 10m
    dist_plot = distance[valid_idx]
    rir_plot = np.abs(rir_causal[valid_idx])
    
    # Lower threshold to 0.03 to catch smaller echoes this time
    peaks, _ = signal.find_peaks(rir_plot, height=0.03, distance=int(0.1 / (speed_of_sound / fs / 2)))
    
    # Exclude direct sound (under 0.3m)
    peaks = peaks[dist_plot[peaks] > 0.3]
    return dist_plot[peaks], rir_plot[peaks]

def run_2d_mapping():
    print("=" * 60)
    print(" EchoMap E5~E8: 2D Room Mapping (Manual Odometry)")
    print("=" * 60)
    
    fs = 48000
    f0, f1 = 4000, 12000
    chirp_duration = 0.1
    recording_duration = 0.5
    chirp_sig = generate_chirp(chirp_duration, fs, f0, f1)
    playback_sig = np.pad(chirp_sig, (0, int(fs * (recording_duration - chirp_duration))))
    
    num_measurements = 3
    step_distance = 0.5 # 50cm step to the right
    positions = []
    all_peaks = []
    
    print("\n[안내] 방의 벽을 마주보고 노트북을 위치시켜 주세요.")
    print(f"총 {num_measurements}번 측정합니다. 각 측정 후 노트북을 오른쪽으로 {step_distance*100}cm 씩 이동해야 합니다.\n")
    
    for i in range(num_measurements):
        input(f"[{i+1}/{num_measurements}] 준비되셨으면 엔터를 눌러 측정을 시작하세요...")
        
        print(f"측정 중 ({i+1})...")
        recorded = sd.playrec(playback_sig, samplerate=fs, channels=1, blocking=True)
        recorded = recorded.flatten()
        
        peak_dists, peak_amps = extract_rir_peaks(recorded, chirp_sig, fs)
        positions.append((i * step_distance, 0.0))
        all_peaks.append(peak_dists)
        
        print(f"-> 측정 완료! 감지된 벽의 거리 후보: {[round(d, 2) for d in peak_dists]} m\n")
        
        if i < num_measurements - 1:
            print(f">>> 노트북을 오른쪽으로 {step_distance*100}cm 이동해 주세요! <<<\n")
            
    print("모든 측정이 완료되었습니다. 2D 맵을 생성합니다...")
    
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect('equal')
    
    # Plot positions and circles
    colors = ['red', 'green', 'blue']
    for i in range(num_measurements):
        x, y = positions[i]
        ax.plot(x, y, marker='o', color=colors[i], markersize=8, label=f'Pos {i+1} (x={x}m)')
        
        for dist in all_peaks[i]:
            circle = plt.Circle((x, y), dist, color=colors[i], fill=False, linestyle='--', alpha=0.5)
            ax.add_patch(circle)
            
    ax.set_xlim(-2, num_measurements * step_distance + 2)
    ax.set_ylim(-1, 8)
    ax.set_title("2D Echo Mapping (Top-down View)")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Distance from Laptop (m)")
    ax.grid(True)
    ax.legend()
    
    # Explanation text
    text_str = "If circles from different positions share a common tangent line,\nthat tangent line represents a flat wall!"
    plt.figtext(0.5, 0.01, text_str, ha="center", fontsize=10, bbox={"facecolor":"orange", "alpha":0.2, "pad":5})
    
    output_filename = "2d_map_result.png"
    plt.tight_layout()
    plt.savefig(output_filename)
    print(f"2D 지도 시각화 완료! {output_filename} 파일을 확인해 주세요.")

if __name__ == "__main__":
    run_2d_mapping()
