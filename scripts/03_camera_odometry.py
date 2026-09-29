import cv2
import numpy as np

def run_visual_odometry():
    print("=" * 60)
    print(" EchoMap E6: Camera Motion Estimation (Visual Odometry)")
    print("=" * 60)
    print("Initializing camera...")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
        
    # Parameters for ShiTomasi corner detection
    feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)
    
    # Parameters for Lucas Kanade optical flow
    lk_params = dict(winSize=(15, 15), maxLevel=2,
                     criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
                     
    ret, old_frame = cap.read()
    if not ret:
        print("Error: Could not read frame from webcam.")
        return
        
    old_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)
    p0 = cv2.goodFeaturesToTrack(old_gray, mask=None, **feature_params)
    
    # Create a mask image for drawing tracks
    mask = np.zeros_like(old_frame)
    
    # Trajectory map canvas (600x600)
    traj_map = np.zeros((600, 600, 3), dtype=np.uint8)
    pos_x, pos_y = 300.0, 300.0 # Start at the center
    
    print("\n[READY] Camera is running.")
    print("-> 노트북을 천천히 좌우/상하로 움직여 보세요!")
    print("-> 영상 화면(Webcam)과 궤적 화면(Trajectory) 두 창이 뜹니다.")
    print("-> 종료하려면 창을 클릭하고 영어 소문자 'q'를 누르세요.\n")
    
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_count += 1
        
        # Calculate optical flow
        if p0 is not None and len(p0) > 0:
            p1, st, err = cv2.calcOpticalFlowPyrLK(old_gray, frame_gray, p0, None, **lk_params)
            
            if p1 is not None:
                good_new = p1[st == 1]
                good_old = p0[st == 1]
                
                # Calculate the average movement of the camera
                if len(good_new) > 0:
                    # dx, dy of features. If features move left (dx < 0), camera moved right.
                    dx = np.mean(good_old[:, 0] - good_new[:, 0]) 
                    dy = np.mean(good_old[:, 1] - good_new[:, 1])
                    
                    # Scale down the pixel movement to fit in the trajectory map
                    scale = 0.5
                    pos_x += dx * scale
                    pos_y += dy * scale
                    
                    # Keep position within canvas bounds
                    pos_x = np.clip(pos_x, 0, 599)
                    pos_y = np.clip(pos_y, 0, 599)
                    
                    # Draw trajectory point
                    cv2.circle(traj_map, (int(pos_x), int(pos_y)), 2, (0, 255, 0), -1)
                
                # Draw optical flow tracks on webcam view
                for i, (new, old) in enumerate(zip(good_new, good_old)):
                    a, b = new.ravel()
                    c, d = old.ravel()
                    mask = cv2.line(mask, (int(a), int(b)), (int(c), int(d)), (0, 0, 255), 2)
                    frame = cv2.circle(frame, (int(a), int(b)), 5, (0, 0, 255), -1)
                    
                # Update previous points
                p0 = good_new.reshape(-1, 1, 2)
                
                # Re-detect features if we lose too many or periodically
                if len(p0) < 15 or frame_count % 30 == 0:
                    new_p0 = cv2.goodFeaturesToTrack(frame_gray, mask=None, **feature_params)
                    if new_p0 is not None:
                        p0 = new_p0
                    mask = np.zeros_like(old_frame) # Clear tracks periodically
            else:
                p0 = cv2.goodFeaturesToTrack(frame_gray, mask=None, **feature_params)
        else:
            p0 = cv2.goodFeaturesToTrack(frame_gray, mask=None, **feature_params)
            
        old_gray = frame_gray.copy()
        
        img = cv2.add(frame, mask)
        
        # Display the results
        cv2.imshow('Webcam - Optical Flow', img)
        cv2.imshow('Estimated Trajectory', traj_map)
        
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
    
    cv2.imwrite("trajectory_result.png", traj_map)
    print(f"\nSaved trajectory map to trajectory_result.png")

if __name__ == "__main__":
    run_visual_odometry()
