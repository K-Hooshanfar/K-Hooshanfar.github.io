// server.js
const express = require('express');
const fetch = require('node-fetch'); // For Node.js 18+, you can use the built-in fetch
require('dotenv').config();
const app = express();

app.use(express.json());

const PORT = process.env.PORT || 3000;

// Sample résumé in Markdown (replace with your own data later)
const resumeMarkdown = `
**Resume of Jane Doe**

**Title:** Software Engineer  
**Skills:** JavaScript, Python, HTML, CSS  
**Experience:**  
- Developed web applications at XYZ Corp  
- Built chatbots and mobile apps  
**Education:**  
- B.S. in Computer Science, University of Example (2018)  
`;

// Chat endpoint
app.post('/chat', async (req, res) => {
  try {
    const { userMessage } = req.body;

    // Construct a prompt with resume data and clear instructions.
    const prompt = `
You are an AI assistant that can only answer questions using the following résumé information:
${resumeMarkdown}

If a question is asked that is not answered in the résumé, reply: "I'm sorry, I can only answer questions about my resume."

User: ${userMessage}
Assistant:`;

    // Call the Gemini API.
    // Replace <GEMINI_API_ENDPOINT> with the actual endpoint from Google AI Studio.
    const apiResponse = await fetch("https://gemini.api.endpoint", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${GEMINI_API_KEY}`  // Your API key stored in an env variable
      },
      body: JSON.stringify({
        model: "gemini-2.0-flash-001", // Using the Gemini Flash 2 model
        prompt: prompt,
        // Add any other parameters required by the Gemini API here.
      })
    });

    const apiData = await apiResponse.json();

    // Assume the API returns a JSON object with a "reply" field.
    const reply = apiData.reply || "No reply received from the Gemini API.";

    res.json({ reply });
  } catch (err) {
    console.error(err);
    res.status(500).json({ reply: "Error: " + err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
