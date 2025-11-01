// let threadId = 1234;

// const chatArea = document.getElementById("chat-area");
// const chatForm = document.getElementById("chat-form");
// const userInput = document.getElementById("user-input");

// chatForm.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   const message = userInput.value.trim();
//   if (!message) return;

//   // add user message
//   addMessage("user", message);
//   userInput.value = "";

//   // add typing indicator
//   const typingEl = addTypingIndicator();

//   try {
//     const res = await fetch(`/chat/${threadId || ""}`, {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({ message, threadId }),
//     });
//     const data = await res.json();

//     threadId = data.thread; // store thread id for next requests

//     typingEl.remove();
//     addMessage("bot", data.response.trim());
//   } catch (err) {
//     typingEl.remove();
//     addMessage("bot", "⚠️ Network error. Please try again.");
//     console.error(err);
//   }
// });

// function addMessage(role, text) {
//   const msg = document.createElement("div");
//   msg.className = `message ${role}`;

//   const avatar = document.createElement("div");
//   avatar.className = "avatar";
//   avatar.textContent = role === "user" ? "U" : "G";

//   const bubble = document.createElement("div");
//   bubble.className = "bubble";
//   bubble.textContent = text;

//   msg.appendChild(avatar);
//   msg.appendChild(bubble);
//   chatArea.appendChild(msg);

//   chatArea.scrollTop = chatArea.scrollHeight;
// }

// function addTypingIndicator() {
//   const msg = document.createElement("div");
//   msg.className = "message bot";
//   const avatar = document.createElement("div");
//   avatar.className = "avatar";
//   avatar.textContent = "G";

//   const typing = document.createElement("div");
//   typing.className = "typing";
//   typing.innerHTML = "<span></span><span></span><span></span>";

//   msg.appendChild(avatar);
//   msg.appendChild(typing);
//   chatArea.appendChild(msg);
//   chatArea.scrollTop = chatArea.scrollHeight;
//   return msg;
// }
