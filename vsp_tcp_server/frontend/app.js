let token = null;
const CHUNK_SIZE = 512 * 1024; // 512KB

// Login Logic
document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const u = document.getElementById("username").value;
    const p = document.getElementById("password").value;

    try {
        const res = await fetch("/api/login", {
            method: "POST",
            body: JSON.stringify({ username: u, password: p })
        });
        
        if (res.ok) {
            const data = await res.json();
            token = data.token;
            document.getElementById("login-section").classList.add("hidden");
            document.getElementById("dashboard").classList.remove("hidden");
            document.getElementById("auth-status").innerText = `User: ${u}`;
            loadVideos();
        } else {
            alert("Login Failed");
        }
    } catch (err) {
        console.error(err);
        alert("Server connection failed");
    }
});

// Upload Logic
document.getElementById("upload-btn").addEventListener("click", async () => {
    const fileInput = document.getElementById("vid-file");
    const titleInput = document.getElementById("vid-title");
    const file = fileInput.files[0];
    
    if (!file) return alert("Select a file first");

    const status = document.getElementById("upload-status");
    const pBar = document.getElementById("progress-bar");
    const pContainer = document.getElementById("progress-container");

    pContainer.classList.remove("hidden");
    status.innerText = "Initializing session...";

    // 1. Create Session
    const initRes = await fetch("/api/newvid", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ title: titleInput.value || file.name, total_size: file.size })
    });
    
    const meta = await initRes.json();
    const uploadId = meta.upload_id;

    // 2. Loop Chunks
    let offset = 0;
    let idx = 0;
    
    while (offset < file.size) {
        const chunk = file.slice(offset, offset + CHUNK_SIZE);
        const buffer = await chunk.arrayBuffer();
        
        const chunkRes = await fetch("/api/upload_chunk", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Upload-Id": uploadId,
                "Chunk-Index": String(idx)
            },
            body: buffer
        });

        if (!chunkRes.ok) {
            status.innerText = "Error uploading chunk " + idx;
            return;
        }

        offset += CHUNK_SIZE;
        idx++;

        // Update UI
        const percent = Math.min(100, Math.round((offset / file.size) * 100));
        pBar.style.width = percent + "%";
        pBar.innerText = percent + "%";
    }

    // 3. Commit
    status.innerText = "Finalizing...";
    const commitRes = await fetch("/api/commit", {
        method: "POST",
        headers: { 
            "Authorization": `Bearer ${token}`,
            "Upload-Id": uploadId 
        }
    });

    if (commitRes.ok) {
        status.innerText = "Upload Complete!";
        loadVideos();
        // Reset inputs
        titleInput.value = "";
        fileInput.value = "";
        setTimeout(() => pContainer.classList.add("hidden"), 3000);
    } else {
        status.innerText = "Commit failed.";
    }
});

async function loadVideos() {
    const res = await fetch("/api/videos", {
        headers: { "Authorization": `Bearer ${token}` }
    });
    const videos = await res.json();
    const grid = document.getElementById("video-grid");
    grid.innerHTML = "";

    videos.forEach(v => {
        const card = document.createElement("div");
        card.className = "video-card";
        card.innerHTML = `
            <h3>${v.title}</h3>
            <p>Size: ${(v.size / 1024 / 1024).toFixed(2)} MB</p>
            <video controls preload="metadata">
                <source src="/api/video/${v.video_id}" type="video/mp4">
            </video>
        `;
        grid.appendChild(card);
    });
}