"""Stage modules: one file per stage, named as in ``fedpress.STAGES``.

Order and resources (CPU stages run in CPU jobs: a GPU idle for 1 h gets the whole job killed):

    fetch     net  video MP4 (Brightcove, re-resolved from the video id), transcript PDF, statement HTML, [VTT]
    audio     cpu  16 kHz mono WAV
    frames    cpu  JPEG frames at frames.fps in one zip + index
    asr       gpu  faster-whisper word timestamps (team-plan clock)
    turns     cpu  transcript speaker turns aligned to ASR (or VTT) times; anchor.json; opening/question/answer
    diarize   gpu  chair voice verification (ECAPA, enrolled on the opening); pyannote optional
    voice     gpu  Powell-only vocal proxy: audeering A/D/V + parselmouth F0 on chair answer chunks
    face      gpu  Powell-only expression proxy: MediaPipe + EmotiEffLib at face.fps on answer frames
    text      gpu  walk-forward ChronoBERT stance (D1; FOMC-RoBERTa cross-check), dictionaries, novelty: statement, answers, questions
    aggregate cpu  per chair answer, per meeting, trailing windows; finalize builds the panel (fedpress.dataset)

The contract each module follows is in fedpress/stage.py and docs/ARCHITECTURE.md.
"""
