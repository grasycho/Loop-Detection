# Loop Detection

A desktop application for detecting duplicate, near-duplicate, and potentially looping frames in video files and image sequences.

Loop Detection uses perceptual image hashing to compare frames efficiently. It can analyze an entire video, a manually selected image sequence, or all supported images inside a folder.

The application is designed for workflows involving:

* Animation loops
* Motion graphics
* Rendered image sequences
* Video editing
* Frame duplication detection
* Loop seam analysis
* Repeated animation frames
* Render validation

---

## Features

### Input Support

* Video file analysis
* Image sequence analysis
* Image folder analysis
* Natural filename sorting for image sequences

### Supported Video Formats

```text
.mp4
.avi
.mov
.mkv
.webm
.mxf
.m4v
```

### Supported Image Formats

```text
.png
.jpg
.jpeg
.tif
.tiff
.bmp
.webp
.dpx
.exr
```

### Detection Features

* Perceptual hashing
* Difference hashing
* Average hashing
* Wavelet hashing
* Adjustable hash size
* Adjustable similarity threshold
* Frame skipping
* Custom frame range
* Consecutive duplicate detection
* Full duplicate search
* Similarity percentage calculation

### Output Features

* Duplicate group table
* Frame indices
* Duplicate count
* Similarity percentage
* First duplicate preview
* CSV export
* JSON export
* Optional duplicate thumbnails

### Interface Features

* Modern CustomTkinter interface
* Dark mode by default
* Light/dark appearance toggle
* Progress bar
* Percentage indicator
* Processing status
* Estimated remaining time
* Cancellation support
* Duplicate preview panel

---

# How It Works

Loop Detection converts every analyzed frame into a compact perceptual hash.

Instead of comparing every pixel directly, the application compares image hashes.

```text
Video / Image Sequence
          │
          ▼
     Read Frame
          │
          ▼
   Generate Image Hash
          │
          ▼
Compare Hash Distances
          │
          ▼
 Distance ≤ Threshold?
      │         │
     YES        NO
      │         │
      ▼         ▼
Duplicate      New Group
 Group
      │
      ▼
Results / Export
```

The lower the hash distance, the more visually similar two frames are.

---

# Installation

## Requirements

Python 3.9 or newer is recommended.

Install the required dependencies:

```bash
pip install customtkinter opencv-python pillow ImageHash numpy
```

---

## Dependencies

| Package       | Purpose                                 |
| ------------- | --------------------------------------- |
| CustomTkinter | Modern desktop interface                |
| OpenCV        | Video and image frame loading           |
| Pillow        | Image conversion and preview generation |
| ImageHash     | Perceptual image hashing                |
| NumPy         | Image-processing dependency             |

---

# Running the Application

Run the script with Python:

```bash
python Loop_Detection_2026_fixed.py
```

If you rename the file:

```bash
python loop_detection.py
```

---

# User Interface

The application is divided into several sections.

```text
┌──────────────────────────────────────────────┐
│              LOOP DETECTION                  │
│           Frame Duplicate Analyser           │
├──────────────────────────────────────────────┤
│                                              │
│  INPUT                                       │
│  [Select Video]                              │
│  [Select Image Sequence]                     │
│  [Select Image Folder]                       │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  DETECTION SETTINGS                          │
│  Hash Method                                 │
│  Hash Size                                   │
│  Threshold                                   │
│  Frame Skip                                  │
│  Frame Range                                 │
│                                              │
│  ☑ Consecutive duplicates only               │
│  ☑ Export thumbnails                         │
│  ☑ Preview first duplicate                   │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  PROGRESS                                    │
│  ████████████████████░░░░                    │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  DUPLICATE PREVIEW                           │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  RESULTS                                     │
│                                              │
│  Group | Count | First | Frames | Similarity │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  [ANALYSE] [Cancel] [Export CSV]             │
│  [Export JSON]                               │
│                                              │
└──────────────────────────────────────────────┘
```

---

# Input

## Analyze a Video

Click:

```text
Select Video
```

Select a supported video file.

The application displays information including:

* Filename
* Resolution
* Frame rate
* Total frame count
* Duration
* Codec
* File size

Example:

```text
animation.mp4 · 1920×1080 · 30.000 fps · 900 frames · 30.00s
```

---

## Analyze an Image Sequence

Click:

```text
Select Image Sequence
```

Select multiple image files.

The application automatically applies natural sorting.

For example:

```text
frame_1.png
frame_2.png
frame_10.png
```

will be processed in the correct sequence order.

---

## Analyze an Image Folder

Click:

```text
Select Image Folder
```

All supported image files inside the selected folder are loaded.

The current implementation scans the selected folder directly and does not recursively scan subfolders.

---

# Detection Settings

## Hash Method

Loop Detection supports four image hashing algorithms.

### pHash — Perceptual Hash

```text
pHash (Perceptual)
```

Recommended for general duplicate detection.

Perceptual hashing is designed to identify images that look visually similar even if their raw pixel data differs slightly.

---

### dHash — Difference Hash

```text
dHash (Difference)
```

Compares gradients and differences between neighboring pixels.

Useful for fast image similarity detection.

---

### aHash — Average Hash

```text
aHash (Average)
```

A simple and fast hashing algorithm based on average pixel brightness.

---

### wHash — Wavelet Hash

```text
wHash (Wavelet)
```

Uses wavelet transformations for image hashing.

Can be useful when analyzing images with different visual characteristics.

---

# Hash Size

Available hash sizes:

```text
8
12
16
24
32
```

Default:

```text
16
```

A larger hash size:

* Provides more detail
* Increases the maximum hash distance
* Can improve discrimination between similar frames
* Requires more processing

A smaller hash size:

* Is faster
* Uses less detail
* May group visually similar but different frames more easily

---

# Threshold

The threshold determines how similar two frame hashes must be before they are considered duplicates.

```text
0 = Exact hash match
Higher values = More permissive matching
```

Available range:

```text
0–30
```

Default:

```text
5
```

### Example

```text
Hash Distance = 0
```

The hashes are identical.

```text
Hash Distance = 3
```

The frames are very similar.

```text
Hash Distance = 15
```

The frames may still be grouped if the threshold is configured to allow that distance.

---

# Frame Skip

Frame Skip controls how frequently frames are analyzed.

Available settings:

```text
1 (every frame)
2
3
4
5
10
```

Example:

```text
Frame Skip = 1
```

Every frame is analyzed.

```text
Frame Skip = 5
```

Only every fifth frame is analyzed.

This can significantly reduce processing time for large videos or long image sequences.

### Important

Frame skipping can miss duplicate frames located between sampled frames.

For the most accurate results:

```text
Frame Skip = 1
```

---

# Frame Range

The application allows analysis of only part of the input.

Settings:

```text
Start: 0
End: 0
```

An End value of:

```text
0
```

means:

```text
Analyze all frames
```

Example:

```text
Start: 100
End: 500
```

Only frames in that range are analyzed.

---

# Consecutive Duplicates Only

Enable:

```text
Consecutive duplicates only
```

to compare each sampled frame only with the immediately previous sampled frame.

This mode is useful for identifying:

* Back-to-back duplicate frames
* Frozen frames
* Accidental repeated frames
* Loop seams
* Adjacent animation duplication

Example:

```text
Frame 100 → Frame 101 → Frame 102

Frame 100 ≈ Frame 101
Frame 101 ≈ Frame 102
```

These frames can be grouped together.

When this option is disabled, the application searches for matching frames throughout the selected range.

---

# Duplicate Detection Modes

## Global Duplicate Search

When:

```text
Consecutive duplicates only = OFF
```

the application compares each frame hash against existing duplicate groups.

This can identify repeated frames that appear far apart in the timeline.

Example:

```text
Frame 10
Frame 300
Frame 900
```

If they are sufficiently similar, they can be grouped together.

This mode is useful for detecting:

* Repeated animation poses
* Duplicated renders
* Reused frames
* Possible looping patterns

---

## Consecutive Duplicate Search

When:

```text
Consecutive duplicates only = ON
```

each sampled frame is compared only with the previous sampled frame.

This is better suited to:

* Duplicate adjacent frames
* Frozen frames
* Accidental frame repetition
* Loop seam inspection

---

# Similarity Percentage

The application calculates similarity from the actual Hamming distance between frame hashes.

Conceptually:

```text
Similarity = 100 × (1 - Hash Distance / Maximum Hash Distance)
```

Results are displayed as:

```text
100%  = Identical hash
95%+  = Very similar
80%+  = Moderately similar
<80%  = Lower similarity
```

The similarity color changes based on the result:

| Similarity    | Status              |
| ------------- | ------------------- |
| 95% and above | High similarity     |
| 80%–94.9%     | Moderate similarity |
| Below 80%     | Lower similarity    |

Note that similarity is based on perceptual hash distance and should not be interpreted as an exact pixel-level similarity measurement.

---

# Progress Tracking

During analysis, the application displays:

* Progress bar
* Percentage completed
* Current frame
* Total frames
* Current timecode or filename
* Estimated remaining time

Example:

```text
67%
Frame 600/900  00:00:20
ETA: 4s
```

Progress calculations account for the selected frame skip value.

---

# Canceling an Analysis

Click:

```text
Cancel
```

to stop the current analysis.

The application checks for cancellation during processing.

When cancelled:

* The analysis stops safely.
* The current run is marked as cancelled.
* Partial results are discarded.
* The Analyze button becomes available again.

---

# Duplicate Preview

When:

```text
Preview first duplicate
```

is enabled, the application displays the first available duplicate group.

The preview includes:

* Thumbnail preview
* Duplicate group information
* Frame indices

The preview is generated from the first stored duplicate frame.

---

# Results

Detected duplicates are displayed in a results table.

| Column     | Description                          |
| ---------- | ------------------------------------ |
| Group      | Duplicate group number               |
| Count      | Number of frames in the group        |
| First      | First detected frame index           |
| All Frames | Frame indices belonging to the group |
| Similarity | Average hash-based similarity        |

Example:

```text
Group  Count  First  All Frames          Similarity
---------------------------------------------------
1      4      10     10, 11, 300, 301    98.7%
2      3      500    500, 501, 502       96.4%
```

Large groups are shortened in the interface after the first several frame indices.

---

# CSV Export

Click:

```text
Export CSV
```

to save the results as a CSV file.

The CSV contains:

```text
Group
Frame Count
Frame Indices
Similarity
```

Example:

```csv
Group,Frame Count,Frame Indices,Similarity
1,4,"10 11 300 301",98.70%
2,3,"500 501 502",96.40%
```

---

# JSON Export

Click:

```text
Export JSON
```

to save the results as structured JSON.

Example:

```json
{
  "group_1": {
    "frames": [10, 11, 300, 301],
    "similarity": 98.7
  },
  "group_2": {
    "frames": [500, 501, 502],
    "similarity": 96.4
  }
}
```

---

# Thumbnail Export

Enable:

```text
Export thumbnails of duplicates
```

before starting the analysis.

After analysis, choose an output folder.

The application creates:

```text
loop_thumbnails/
```

Example:

```text
loop_thumbnails/
├── group_0001_frame10.jpg
├── group_0002_frame500.jpg
└── group_0003_frame850.jpg
```

Thumbnails are generated from the representative frame stored for each duplicate group.

---

# Workflow

## Basic Workflow

### Step 1 — Select Input

Choose one of:

```text
Select Video
Select Image Sequence
Select Image Folder
```

---

### Step 2 — Configure Detection

Recommended starting settings:

```text
Hash Method:
pHash (Perceptual)

Hash Size:
16

Threshold:
5

Frame Skip:
1 (every frame)
```

---

### Step 3 — Optional Settings

Choose whether to enable:

```text
Consecutive duplicates only
```

```text
Export thumbnails of duplicates
```

```text
Preview first duplicate
```

---

### Step 4 — Start Analysis

Click:

```text
ANALYSE
```

---

### Step 5 — Review Results

Inspect:

* Duplicate groups
* Frame indices
* Similarity percentages
* Preview image

---

### Step 6 — Export

Export results as:

```text
CSV
```

or:

```text
JSON
```

---

# Recommended Settings

## Detect Exact Duplicate Frames

```text
Hash Method: pHash
Hash Size: 16
Threshold: 0
Frame Skip: 1
```

---

## Detect Visually Similar Frames

```text
Hash Method: pHash
Hash Size: 16
Threshold: 5
Frame Skip: 1
```

---

## Fast Large Video Analysis

```text
Hash Method: dHash
Hash Size: 8 or 16
Threshold: 5
Frame Skip: 5
```

---

## Detect Frozen Frames

```text
Consecutive duplicates only: ON
Frame Skip: 1
Threshold: 0–5
```

---

## Analyze Animation Loop Seams

For investigating potential loop issues:

```text
Hash Method: pHash
Hash Size: 16
Threshold: 3–8
Frame Skip: 1
Consecutive duplicates only: ON
```

Depending on the animation, you may also need to manually inspect the first and last frames.

---

# Technical Architecture

The application consists of several major components.

```text
LoopDetectorApp
│
├── User Interface
│   ├── Input Selection
│   ├── Detection Settings
│   ├── Progress
│   ├── Preview
│   └── Results
│
├── Input Processing
│   ├── Video Loading
│   ├── Image Sequence Loading
│   └── Folder Scanning
│
├── Detection Engine
│   ├── Frame Reading
│   ├── Image Hashing
│   ├── Hash Comparison
│   ├── Duplicate Grouping
│   └── Similarity Calculation
│
├── Results
│   ├── Result Table
│   ├── Preview
│   ├── CSV Export
│   └── JSON Export
│
└── Thumbnail Export
```

---

# Main Classes

## `LoopDetectorApp`

The main application class.

Responsible for:

* Application interface
* File selection
* Detection settings
* Background processing
* Progress updates
* Result generation
* Export functionality

---

## `ResultTable`

A scrollable results table.

Displays:

* Group number
* Frame count
* First frame
* Duplicate frame indices
* Similarity percentage

---

## `Tooltip`

Provides hover tooltips for selected interface controls.

---

# Duplicate Detection Algorithm

The analysis process follows these steps:

```text
1. Load frame
       │
       ▼
2. Convert BGR → RGB
       │
       ▼
3. Convert frame → PIL Image
       │
       ▼
4. Generate perceptual hash
       │
       ▼
5. Compare hash distances
       │
       ▼
6. Find closest compatible group
       │
       ├── Match → Add frame to group
       │
       └── No Match → Create new group
       │
       ▼
7. Keep groups containing 2+ frames
       │
       ▼
8. Calculate similarity
       │
       ▼
9. Display results
```

---

# Threading

Analysis runs in a background thread.

This prevents the application from performing the complete frame analysis directly inside the main UI callback.

UI updates are scheduled through:

```python
self.root.after(...)
```

This is used for:

* Progress updates
* Status changes
* Analysis completion
* Error reporting
* Cancellation results

---

# Image Sequence Sorting

Image sequences are naturally sorted.

Example:

```text
frame_1.png
frame_2.png
frame_3.png
frame_10.png
frame_11.png
```

rather than alphabetical sorting:

```text
frame_1.png
frame_10.png
frame_11.png
frame_2.png
frame_3.png
```

This is important when working with numbered render sequences.

---

# Project Structure

Example:

```text
Loop-Detection/
│
├── Loop_Detection_2026_fixed.py
├── README.md
│
└── requirements.txt
```

---

# Example `requirements.txt`

```text
customtkinter
opencv-python
Pillow
ImageHash
numpy
```

Install dependencies with:

```bash
pip install -r requirements.txt
```

---

# Limitations

## Perceptual Hashing Is Not Pixel Comparison

The application compares image hashes.

Two frames may:

* Have different pixels but similar hashes
* Have visually similar content
* Be grouped together depending on the threshold

For pixel-perfect duplicate validation, an additional pixel comparison system would be required.

---

## Frame Skip Can Miss Duplicates

Using:

```text
Frame Skip > 1
```

means some frames are not analyzed.

For maximum accuracy:

```text
Frame Skip = 1
```

---

## Large Inputs Require Time

Processing speed depends on:

* Video resolution
* Number of frames
* Image resolution
* Selected hash algorithm
* Hash size
* Frame skip
* Hardware performance

---

## Global Matching Complexity

When consecutive-only mode is disabled, each new frame hash can be compared against existing groups.

Very large videos with many visually unique frames may therefore take longer to process.

---

# Performance Tips

For very large files:

```text
Use dHash
Use Hash Size 8 or 16
Use Frame Skip 5 or 10
Analyze a limited frame range
```

For maximum detection accuracy:

```text
Use pHash
Use Hash Size 16 or higher
Use Frame Skip 1
Use a conservative threshold
```

---

# Future Improvements

Potential future features include:

* Side-by-side duplicate comparison
* Timeline visualization
* First/last frame loop comparison
* Video scrubbing
* Frame jump navigation
* Duplicate confidence sorting
* Exact pixel comparison mode
* SSIM comparison
* GPU acceleration
* Parallel hash generation
* Recursive image folder scanning
* Drag-and-drop support
* Batch video analysis
* HTML report export
* PDF report export
* Duplicate frame deletion tools
* Video trimming integration

---

# Troubleshooting

## OpenCV Cannot Open Video

Make sure:

* The video file is not corrupted.
* Your OpenCV installation supports the codec.
* FFmpeg support is available in your OpenCV build.

Try converting the video to:

```text
MP4 / H.264
```

if necessary.

---

## No Duplicates Found

Try:

* Increasing the threshold.
* Using a different hash algorithm.
* Reducing the frame skip value.
* Analyzing every frame.

Example:

```text
Threshold: 5 → 10
Frame Skip: 5 → 1
```

---

## Too Many False Positives

Try:

* Reducing the threshold.
* Increasing hash size.
* Switching to pHash.
* Using consecutive-only mode.

---

## Image Files Are Missing

Verify that the files use supported extensions.

Supported formats include:

```text
PNG
JPG
JPEG
TIF
TIFF
BMP
WEBP
DPX
EXR
```

Actual readability of formats such as DPX or EXR also depends on the OpenCV build installed on the system.

---

# License

No license is currently included with the project.

If you plan to publish or distribute the project, consider adding:

* MIT License
* Apache License 2.0
* GPL-3.0

---

# Summary

Loop Detection is a Python desktop tool for analyzing videos and image sequences to identify:

```text
Duplicate Frames
Near-Duplicate Frames
Repeated Animation Frames
Frozen Frames
Potential Loop Seams
```

It combines:

```text
Python
+
CustomTkinter
+
OpenCV
+
Pillow
+
ImageHash
```

to provide an interactive frame-analysis workflow with configurable perceptual hashing, progress tracking, previews, duplicate grouping, and exportable reports.
