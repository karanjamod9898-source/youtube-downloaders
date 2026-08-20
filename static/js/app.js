document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const analyzeForm = document.getElementById("analyze-form");
    const youtubeUrlInput = document.getElementById("youtube-url");
    const btnPaste = document.getElementById("btn-paste");
    const btnAnalyze = document.getElementById("btn-analyze");
    const errorBox = document.getElementById("error-box");
    const errorMessage = document.getElementById("error-message");
    
    const loadingBox = document.getElementById("loading-box");
    const loadingTitle = document.getElementById("loading-title");
    const loadingSubtitle = document.getElementById("loading-subtitle");
    
    const previewCard = document.getElementById("preview-card");
    const videoThumbnail = document.getElementById("video-thumbnail");
    const videoDuration = document.getElementById("video-duration");
    const videoTitle = document.getElementById("video-title");
    const videoUploader = document.getElementById("video-uploader").querySelector("span");
    const videoGenre = document.getElementById("video-genre");
    const videoUploadDate = document.getElementById("video-upload-date").querySelector("span");
    
    // Quick Panel elements
    const tabToggleAudio = document.getElementById("tab-toggle-audio");
    const tabToggleVideo = document.getElementById("tab-toggle-video");
    const quickAudioOptions = document.getElementById("quick-audio-options");
    const quickVideoOptions = document.getElementById("quick-video-options");
    const quickPanelBorder = document.getElementById("quick-panel-border");
    const quickMp3Quality = document.getElementById("quick-mp3-quality");
    const quickMp4Quality = document.getElementById("quick-mp4-quality");
    const btnQuickMp3 = document.getElementById("btn-quick-mp3");
    const btnQuickMp4 = document.getElementById("btn-quick-mp4");

    // Preview Panel elements
    const mp3Quality = document.getElementById("mp3-quality");
    const btnDownloadMp3 = document.getElementById("btn-download-mp3");
    const mp4Quality = document.getElementById("mp4-quality");
    const btnDownloadMp4 = document.getElementById("btn-download-mp4");
    
    // Progress Elements
    const progressBox = document.getElementById("progress-box");
    const progressStatusTitle = document.getElementById("progress-status-title");
    const progressStatusSub = document.getElementById("progress-status-sub");
    const progressPercent = document.getElementById("progress-percent");
    const progressBarFill = document.getElementById("progress-bar-fill");
    
    // Steps Elements
    const steps = {
        preparing: document.getElementById("step-preparing"),
        downloading: document.getElementById("step-downloading"),
        processing: document.getElementById("step-processing"),
        embedding: document.getElementById("step-embedding"),
        finalizing: document.getElementById("step-finalizing")
    };

    // History Elements
    const historyCard = document.getElementById("history-card");
    const historyList = document.getElementById("history-list");
    const btnClearHistory = document.getElementById("btn-clear-history");

    // Toast Container
    const toastContainer = document.getElementById("toast-container");

    // State Variables
    let currentVideoDetails = null;
    let pollInterval = null;
    let activeQuickTab = "audio"; // "audio" or "video"

    // Helper: Formats download duration
    function formatDuration(seconds) {
        if (!seconds || seconds <= 0) return "00:00";
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        const pad = (num) => String(num).padStart(2, "0");
        return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
    }

    // Helper: Format raw date string "YYYYMMDD" to human readable "DD MMM YYYY"
    function formatDate(rawDateStr) {
        if (!rawDateStr || rawDateStr.length < 8) return "Unknown date";
        const y = rawDateStr.substring(0, 4);
        const m = parseInt(rawDateStr.substring(4, 6)) - 1;
        const d = parseInt(rawDateStr.substring(6, 8));
        const dateObj = new Date(y, m, d);
        return dateObj.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
    }

    // Custom Dropdown Menu Controller
    function initCustomDropdowns() {
        const dropdowns = document.querySelectorAll(".custom-dropdown");

        dropdowns.forEach(dropdown => {
            const trigger = dropdown.querySelector(".select-trigger");
            const optionsList = dropdown.querySelector(".select-options");
            const chevron = dropdown.querySelector(".chevron-icon");
            const targetSelectId = dropdown.getAttribute("data-target");
            const targetSelect = document.getElementById(targetSelectId);

            if (!trigger || !optionsList || !targetSelect) return;

            // Toggle active menu view
            trigger.addEventListener("click", (e) => {
                e.stopPropagation();
                
                // Auto-close other selectors
                document.querySelectorAll(".select-options").forEach(optList => {
                    if (optList !== optionsList) {
                        optList.classList.add("hidden");
                        optList.parentElement.querySelector(".chevron-icon")?.classList.remove("rotate-180");
                    }
                });

                const isHidden = optionsList.classList.contains("hidden");
                if (isHidden) {
                    optionsList.classList.remove("hidden");
                    chevron?.classList.add("rotate-180");
                } else {
                    optionsList.classList.add("hidden");
                    chevron?.classList.remove("rotate-180");
                }
            });

            // Set option click triggers
            dropdown.querySelectorAll(".select-option").forEach(option => {
                option.addEventListener("click", () => {
                    const value = option.getAttribute("data-value");
                    const text = option.textContent.trim();

                    // Update visible selected value
                    trigger.querySelector(".selected-text").textContent = text;
                    
                    // Sync original select value
                    targetSelect.value = value;
                    
                    // Dispatch change updates
                    targetSelect.dispatchEvent(new Event("change"));

                    // Close list
                    optionsList.classList.add("hidden");
                    chevron?.classList.remove("rotate-180");
                });
            });
        });

        // Click outside handler
        document.addEventListener("click", () => {
            document.querySelectorAll(".select-options").forEach(optList => {
                optList.classList.add("hidden");
            });
            document.querySelectorAll(".chevron-icon").forEach(chev => {
                chev.classList.remove("rotate-180");
            });
        });
    }

    // Trigger custom selects initialization
    initCustomDropdowns();

    // Helper: Toast Notifications (Premium Glass Style)
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = "toast-card toast-in p-4 rounded-2xl flex items-start space-x-3 pointer-events-auto w-full transition-all duration-300 ";
        
        let iconClass = "fa-solid fa-circle-info text-blue-500";
        if (type === "success") {
            iconClass = "fa-solid fa-circle-check text-emerald-500";
        } else if (type === "error") {
            iconClass = "fa-solid fa-circle-exclamation text-red-500";
        }

        toast.innerHTML = `
            <i class="${iconClass} text-sm shrink-0 mt-0.5 animate-pulse"></i>
            <div class="flex-grow text-xs font-bold leading-normal">${message}</div>
            <button class="text-slate-400 hover:text-slate-200 transition shrink-0">&times;</button>
        `;

        toast.querySelector("button").addEventListener("click", () => {
            toast.classList.replace("toast-in", "toast-out");
            setTimeout(() => toast.remove(), 250);
        });

        toastContainer.appendChild(toast);
        
        // Auto-remove after 4.5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.classList.replace("toast-in", "toast-out");
                setTimeout(() => toast.remove(), 250);
            }
        }, 4500);
    }

    // Helper: Show/Hide Utilities
    function show(el) { el.classList.remove("hidden"); }
    function hide(el) { el.classList.add("hidden"); }

    // Segmented capsule switcher control
    function switchQuickTab(tab) {
        activeQuickTab = tab;
        if (tab === "audio") {
            tabToggleAudio.className = "capsule-btn active-audio";
            tabToggleVideo.className = "capsule-btn tab-inactive";
            
            // Switch panel borders
            quickPanelBorder.classList.remove("active-border-video");
            quickPanelBorder.classList.add("active-border-audio");
            
            show(quickAudioOptions);
            hide(quickVideoOptions);
        } else {
            tabToggleVideo.className = "capsule-btn active-video";
            tabToggleAudio.className = "capsule-btn tab-inactive";
            
            // Switch panel borders
            quickPanelBorder.classList.remove("active-border-audio");
            quickPanelBorder.classList.add("active-border-video");
            
            show(quickVideoOptions);
            hide(quickAudioOptions);
        }
    }

    tabToggleAudio.addEventListener("click", () => switchQuickTab("audio"));
    tabToggleVideo.addEventListener("click", () => switchQuickTab("video"));

    // Clipboard Paste Button
    btnPaste.addEventListener("click", async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                youtubeUrlInput.value = text;
                showToast("YouTube link pasted from clipboard!", "success");
            }
        } catch (err) {
            showToast("Failed to read from clipboard. Please paste manually.", "error");
        }
    });

    // Handle URL Analysis
    analyzeForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const url = youtubeUrlInput.value.trim();
        if (!url) return;

        hide(errorBox);
        hide(previewCard);
        hide(progressBox);
        
        loadingTitle.textContent = "Analyzing YouTube Video";
        loadingSubtitle.textContent = "Negotiating handshake & extracting metadata...";
        show(loadingBox);
        setTimeout(() => { loadingBox.scrollIntoView({ behavior: "smooth", block: "center" }); }, 100);
        btnAnalyze.disabled = true;

        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url })
            });

            if (!response.ok) {
                let errorText = "Metadata parsing failed.";
                try {
                    const errorData = await response.json();
                    errorText = errorData.detail || errorText;
                } catch (_) {
                    errorText = `Error ${response.status}: ${response.statusText}`;
                }
                throw new Error(errorText);
            }

            const data = await response.json();

            // Store metadata state
            currentVideoDetails = data;
            
            // Populate previews
            videoThumbnail.src = data.thumbnail || "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=600&auto=format&fit=crop";
            videoTitle.textContent = data.title;
            videoUploader.textContent = data.uploader || "Unknown Channel";
            videoDuration.textContent = formatDuration(data.duration);
            videoUploadDate.textContent = formatDate(data.upload_date);
            
            if (data.genre) {
                videoGenre.textContent = data.genre;
                show(videoGenre);
            } else {
                hide(videoGenre);
            }

            hide(loadingBox);
            show(previewCard);
            setTimeout(() => { previewCard.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, 100);
            showToast("Video analyzed successfully!", "success");
        } catch (err) {
            hide(loadingBox);
            errorMessage.textContent = err.message;
            show(errorBox);
            setTimeout(() => { errorBox.scrollIntoView({ behavior: "smooth", block: "center" }); }, 100);
            showToast(err.message, "error");
        } finally {
            btnAnalyze.disabled = false;
        }
    });

    // Step Status Helper
    function updateStepsTimeline(activeStepKey) {
        Object.keys(steps).forEach(key => {
            steps[key].className = "flex items-center space-x-2 text-xs text-slate-400 font-bold";
            const icon = steps[key].querySelector("i");
            icon.className = "fa-solid fa-circle-check";
        });

        const keys = Object.keys(steps);
        const activeIndex = keys.indexOf(activeStepKey);

        for (let i = 0; i <= activeIndex; i++) {
            const key = keys[i];
            if (i < activeIndex) {
                steps[key].className = "flex items-center space-x-2 text-xs text-emerald-500 font-bold";
                steps[key].querySelector("i").className = "fa-solid fa-circle-check text-emerald-500";
            } else {
                steps[key].className = "flex items-center space-x-2 text-xs text-rose-500 font-extrabold animate-pulse";
                steps[key].querySelector("i").className = "fa-solid fa-circle-notch text-rose-500 animate-spin";
            }
        }
    }

    // Trigger standard download job
    async function startDownload(format, quality) {
        if (!currentVideoDetails) return;

        hide(previewCard);
        hide(errorBox);
        
        // Reset progress bar
        progressPercent.textContent = "0%";
        progressBarFill.style.width = "0%";
        progressStatusTitle.textContent = "Requesting download task...";
        progressStatusSub.textContent = "Spawning download worker thread...";
        updateStepsTimeline("preparing");
        show(progressBox);
        setTimeout(() => { progressBox.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, 100);

        try {
            const response = await fetch("/api/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: currentVideoDetails.url,
                    format: format,
                    quality: quality
                })
            });

            if (!response.ok) {
                let errorText = "Unable to start download thread.";
                try {
                    const errorData = await response.json();
                    errorText = errorData.detail || errorText;
                } catch (_) {}
                throw new Error(errorText);
            }

            const data = await response.json();
            showToast("Download process scheduled successfully.", "info");
            
            // Poll progress
            pollTaskStatus(data.task_id, {
                title: currentVideoDetails.title,
                uploader: currentVideoDetails.uploader,
                thumbnail: currentVideoDetails.thumbnail,
                url: currentVideoDetails.url,
                format: format,
                quality: quality
            });

        } catch (err) {
            hide(progressBox);
            errorMessage.textContent = err.message;
            show(errorBox);
            show(previewCard);
            setTimeout(() => { errorBox.scrollIntoView({ behavior: "smooth", block: "center" }); }, 100);
            showToast(err.message, "error");
        }
    }

    // Poll Progress Status
    function pollTaskStatus(taskId, metadata) {
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/progress/${taskId}`);
                if (!response.ok) throw new Error("Synchronization disconnected.");

                const data = await response.json();
                const status = data.status;
                const progress = data.progress || 0;
                const error = data.error;

                progressPercent.textContent = `${progress}%`;
                progressBarFill.style.width = `${progress}%`;

                if (status === "preparing") {
                    progressStatusTitle.textContent = "Configuring download pipeline...";
                    progressStatusSub.textContent = "Warming up environment engine...";
                    updateStepsTimeline("preparing");
                } 
                else if (status === "fetching video information" || status === "fetching thumbnail") {
                    progressStatusTitle.textContent = "Negotiating YouTube links...";
                    progressStatusSub.textContent = `Resolving: ${status}...`;
                    updateStepsTimeline("preparing");
                }
                else if (status.startsWith("downloading")) {
                    progressStatusTitle.textContent = "Retrieving media streams...";
                    const byteInfo = status.includes("(") ? status.substring(status.indexOf("(")) : "";
                    progressStatusSub.textContent = `Downloading ${byteInfo} (${progress}%)`;
                    updateStepsTimeline("downloading");
                } 
                else if (status.startsWith("processing")) {
                    progressStatusTitle.textContent = "Converting audio (FFmpeg)...";
                    progressStatusSub.textContent = "Running lossless stream converter...";
                    updateStepsTimeline("processing");
                } 
                else if (status.startsWith("embedding")) {
                    progressStatusTitle.textContent = "Tagging Artwork cover & tags...";
                    progressStatusSub.textContent = "Injecting APIC metadata headers...";
                    updateStepsTimeline("embedding");
                } 
                else if (status === "finalizing") {
                    progressStatusTitle.textContent = "Wrapping up media files...";
                    progressStatusSub.textContent = "Caching package output...";
                    updateStepsTimeline("finalizing");
                } 
                else if (status === "ready") {
                    clearInterval(pollInterval);
                    
                    // Mark timeline steps complete
                    Object.keys(steps).forEach(key => {
                        steps[key].className = "flex items-center space-x-2 text-xs text-emerald-500 font-bold";
                        steps[key].querySelector("i").className = "fa-solid fa-circle-check text-emerald-500";
                    });

                    progressStatusTitle.textContent = "Download completed successfully!";
                    progressStatusSub.textContent = "Starting attachment download now...";
                    progressPercent.textContent = "100%";
                    progressBarFill.style.width = "100%";

                    showToast("Success! Serving attachment download.", "success");

                    // Trigger direct attachment download
                    window.location.href = `/api/retrieve/${taskId}`;

                    // Log to Session History
                    saveToHistory({
                        title: metadata.title,
                        uploader: metadata.uploader,
                        thumbnail: metadata.thumbnail,
                        url: metadata.url,
                        format: metadata.format.toUpperCase(),
                        quality: metadata.quality === "best" || metadata.quality === "1080" ? "HD" : `${metadata.quality}k`,
                        status: "Success",
                        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    });

                    // Hide progress overlay and return to main panel
                    setTimeout(() => {
                        hide(progressBox);
                        if (currentVideoDetails) {
                            show(previewCard);
                        }
                    }, 3500);
                } 
                else if (status === "error") {
                    clearInterval(pollInterval);
                    hide(progressBox);
                    errorMessage.textContent = error || "Internal downloader error occurred.";
                    show(errorBox);
                    showToast(error || "Processing failed.", "error");

                    // Log error to history
                    saveToHistory({
                        title: metadata.title,
                        uploader: metadata.uploader,
                        thumbnail: metadata.thumbnail,
                        url: metadata.url,
                        format: metadata.format.toUpperCase(),
                        quality: metadata.quality,
                        status: "Failed",
                        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    });

                    if (currentVideoDetails) show(previewCard);
                }

            } catch (err) {
                clearInterval(pollInterval);
                hide(progressBox);
                errorMessage.textContent = "Lost sync with server downloader task manager.";
                show(errorBox);
                showToast("Connection to downloader failed.", "error");
                if (currentVideoDetails) show(previewCard);
            }
        }, 1000);
    }

    // Trigger quick download direct (without metadata analyze step)
    async function triggerQuickDownload(format, quality) {
        const url = youtubeUrlInput.value.trim();
        if (!url) {
            showToast("Please enter a YouTube video URL first!", "error");
            return;
        }

        hide(errorBox);
        hide(previewCard);
        
        progressStatusTitle.textContent = "Starting Quick Pipeline...";
        progressStatusSub.textContent = "Handshaking with server...";
        updateStepsTimeline("preparing");
        show(progressBox);
        setTimeout(() => { progressBox.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, 100);

        try {
            const response = await fetch("/api/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: url,
                    format: format,
                    quality: quality
                })
            });

            if (!response.ok) {
                let errorText = "Quick download request failed.";
                try {
                    const errorData = await response.json();
                    errorText = errorData.detail || errorText;
                } catch (_) {}
                throw new Error(errorText);
            }

            const data = await response.json();
            showToast("Quick download process started...", "info");
            
            // Poll progress
            pollTaskStatus(data.task_id, {
                title: "Quick Download Item",
                uploader: "YTFlow Engine",
                thumbnail: "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=100&auto=format&fit=crop",
                url: url,
                format: format,
                quality: quality
            });

        } catch (err) {
            hide(progressBox);
            errorMessage.textContent = err.message;
            show(errorBox);
            setTimeout(() => { errorBox.scrollIntoView({ behavior: "smooth", block: "center" }); }, 100);
            showToast(err.message, "error");
        }
    }

    // --- LocalStorage Session History Manager ---
    function loadHistory() {
        try {
            const data = localStorage.getItem("ytflow_history");
            return data ? JSON.parse(data) : [];
        } catch (_) {
            return [];
        }
    }

    function saveToHistory(item) {
        const history = loadHistory();
        const idx = history.findIndex(h => h.url === item.url && h.format === item.format);
        if (idx !== -1) {
            history.splice(idx, 1); // remove old record
        }
        history.unshift(item);
        
        if (history.length > 6) history.pop(); // cap history
        
        localStorage.setItem("ytflow_history", JSON.stringify(history));
        renderHistory();
    }

    function deleteFromHistory(url, format) {
        let history = loadHistory();
        const idx = history.findIndex(h => h.url === url && h.format === format);
        if (idx !== -1) {
            history.splice(idx, 1);
            localStorage.setItem("ytflow_history", JSON.stringify(history));
            renderHistory();
            showToast("Item deleted from history.", "info");
        }
    }

    function renderHistory() {
        const history = loadHistory();
        if (history.length === 0) {
            historyCard.classList.add("hidden");
            historyList.innerHTML = "";
            return;
        }

        historyCard.classList.remove("hidden");
        historyList.innerHTML = "";
        history.forEach((item) => {
            const row = document.createElement("div");
            row.className = "flex flex-col sm:flex-row sm:items-center justify-between p-3.5 bg-slate-500/5 border border-slate-200/10 dark:border-slate-800/20 rounded-2xl hover:border-slate-200/25 dark:hover:border-slate-800/40 transition duration-150 gap-3 sm:gap-4";
            
            const isSuccess = item.status === "Success";
            const badgeClass = isSuccess 
                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-500" 
                : "bg-red-500/10 border-red-500/20 text-red-500";
            
            const formatBadge = item.format === "MP3"
                ? "bg-amber-500/10 border-amber-500/20 text-amber-500"
                : "bg-emerald-500/10 border-emerald-500/20 text-emerald-500";

            row.innerHTML = `
                <div class="flex items-center space-x-3 min-w-0 flex-grow cursor-pointer" title="Load this URL">
                    <img src="${item.thumbnail || ''}" alt="Thumb" class="w-12 h-9 rounded object-cover border border-slate-200/10 dark:border-slate-900 shrink-0">
                    <div class="min-w-0 flex-grow">
                        <h4 class="text-xs sm:text-sm font-bold text-slate-800 dark:text-slate-100 truncate leading-normal">${item.title}</h4>
                        <div class="flex items-center space-x-2 text-[10px] text-slate-400 font-semibold mt-0.5 min-w-0">
                            <span class="truncate max-w-[120px] sm:max-w-none block" title="${item.uploader}">${item.uploader}</span>
                            <span class="text-slate-650">&bull;</span>
                            <span class="shrink-0">${item.timestamp}</span>
                        </div>
                    </div>
                </div>
                <div class="flex items-center justify-between sm:justify-end space-x-2 shrink-0 w-full sm:w-auto mt-2.5 sm:mt-0 pt-2.5 sm:pt-0 border-t border-slate-200/5 dark:border-slate-850 sm:border-t-0">
                    <div class="flex items-center space-x-1.5">
                        <span class="text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded border ${formatBadge}">${item.format} (${item.quality})</span>
                        <span class="text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded border ${badgeClass}">${item.status}</span>
                    </div>
                    <div class="flex items-center space-x-1.5">
                        <button class="btn-copy-history p-1.5 bg-slate-900/20 dark:bg-slate-950/40 border border-slate-200/10 dark:border-slate-800/30 rounded-lg text-slate-400 hover:text-red-500 transition cursor-pointer" title="Load URL">
                            <i class="fa-solid fa-share text-xs"></i>
                        </button>
                        <button class="btn-delete-history p-1.5 bg-slate-900/20 dark:bg-slate-950/40 border border-slate-200/10 dark:border-slate-800/30 rounded-lg text-slate-400 hover:text-red-500 transition cursor-pointer" title="Delete from History">
                            <i class="fa-solid fa-trash text-xs"></i>
                        </button>
                    </div>
                </div>
            `;

            // Row click actions
            row.querySelector(".flex-grow").addEventListener("click", () => {
                youtubeUrlInput.value = item.url;
                showToast("YouTube link loaded.", "success");
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });

            row.querySelector(".btn-copy-history").addEventListener("click", (e) => {
                e.stopPropagation();
                youtubeUrlInput.value = item.url;
                showToast("YouTube link loaded.", "success");
            });

            row.querySelector(".btn-delete-history").addEventListener("click", (e) => {
                e.stopPropagation();
                deleteFromHistory(item.url, item.format);
            });

            historyList.appendChild(row);
        });
    }

    btnClearHistory.addEventListener("click", () => {
        localStorage.removeItem("ytflow_history");
        renderHistory();
        showToast("History log cleared.", "info");
    });
    // Button event connections
    btnDownloadMp3.addEventListener("click", () => {
        startDownload("mp3", mp3Quality.value);
    });

    btnDownloadMp4.addEventListener("click", () => {
        startDownload("mp4", mp4Quality.value);
    });

    btnQuickMp3.addEventListener("click", () => {
        triggerQuickDownload("mp3", quickMp3Quality.value);
    });

    btnQuickMp4.addEventListener("click", () => {
        triggerQuickDownload("mp4", quickMp4Quality.value);
    });

    // Load history
    renderHistory();
});
