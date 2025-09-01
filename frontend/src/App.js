import React, { useEffect, useRef, useState } from "react";

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [file, setFile] = useState(null);

  const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";
  const chatEndRef = useRef(null);

  // Auto-scroll to the bottom whenever messages change
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: input, k: 4 }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }

      const data = await res.json();
      const botReply =
        (data?.answer || "No response.") +
        (Array.isArray(data?.sources) && data.sources.length
          ? `\n\nSources: ${data.sources.join(", ")}`
          : "");
      setMessages((prev) => [...prev, { sender: "bot", text: botReply }]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "Error contacting backend." },
      ]);
    }

    setInput("");
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  const handleFileChange = (e) => {
    setFile(e.target.files?.[0] || null);
  };

  const uploadPDF = async () => {
    if (!file) return alert("Please select a file first.");

    const formData = new FormData();
    formData.append("files", file); // must be 'files' to match backend

    try {
      const res = await fetch(`${API_URL}/api/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: `Uploaded "${file.name}". Indexed ${data.indexed || 0} chunks from ${
            data.files ?? data.saved ?? 1
          } file(s).`,
        },
      ]);
      setFile(null);
    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "Upload failed." },
      ]);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <h2 style={{ margin: "16px 0 12px" }}> AI Studio</h2>

        {/* Chat Box (only this scrolls) */}
        <div style={styles.chatBox}>
          {messages.map((msg, i) => (
            <div
              key={i}
              style={{
                ...styles.message,
                alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
                backgroundColor: msg.sender === "user" ? "#0078D4" : "#333",
              }}
            >
              <strong>{msg.sender === "user" ? "You" : "Bot"}:</strong>{" "}
              <span style={{ whiteSpace: "pre-wrap" }}>{msg.text}</span>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Footer (fixed in layout; does NOT scroll) */}
        <div style={styles.footer}>
          <div style={styles.inputRow}>
            <input
              type="text"
              placeholder="Type a message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              style={styles.input}
            />
            <button onClick={sendMessage} style={styles.button}>
              Send
            </button>
          </div>

          <div style={styles.uploadRow}>
            <input
              type="file"
              accept=".pdf,.txt,.md"
              onChange={handleFileChange}
              style={{ color: "#f1f1f1" }}
            />
            <button onClick={uploadPDF} style={styles.uploadButton}>
              Upload PDF
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* --------- Styles --------- */
const styles = {
  // Full-page dark background; prevent page scrolling
  page: {
    background: "#121212",
    color: "#f1f1f1",
    height: "100vh",
    width: "100vw",
    overflow: "hidden",
  },

  // App frame: vertical layout, chat grows, footer pinned
  container: {
    maxWidth: "min(1200px, 96vw)",
    height: "100%",
    margin: "0 auto",
    padding: "0 24px 16px",
    display: "flex",
    flexDirection: "column",
  },

  chatBox: {
    flex: 1, // take all remaining space
    display: "flex",
    flexDirection: "column",
    gap: 12,
    overflowY: "auto", // <-- only this scrolls
    border: "1px solid #2a2a2a",
    borderRadius: 16,
    padding: 16,
    backgroundColor: "#1e1e1e",
  },

  message: {
    maxWidth: "88%",
    padding: "10px 14px",
    borderRadius: 14,
    fontSize: 16,
    lineHeight: 1.4,
    color: "#fff",
  },

  footer: {
    background: "#121212",
    borderTop: "1px solid #2a2a2a",
    paddingTop: 10,
    paddingBottom: 8,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },

  inputRow: {
    display: "flex",
    gap: 12,
  },

  input: {
    flex: 1,
    padding: 12,
    borderRadius: 10,
    border: "1px solid #555",
    fontSize: 16,
    backgroundColor: "#2c2c2c",
    color: "#f1f1f1",
  },

  button: {
    padding: "12px 18px",
    borderRadius: 10,
    border: "none",
    backgroundColor: "#007BFF",
    color: "#fff",
    cursor: "pointer",
    fontSize: 16,
  },

  uploadRow: {
    display: "flex",
    gap: 12,
    alignItems: "center",
  },

  uploadButton: {
    padding: "10px 14px",
    backgroundColor: "#28a745",
    border: "none",
    borderRadius: 8,
    color: "#fff",
    cursor: "pointer",
    fontSize: 14,
  },
};

export default App;
