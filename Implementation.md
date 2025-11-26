# Task 15: MAS Coordinator - Complete Implementation Guide

## 📋 Overview

This guide provides complete step-by-step instructions for setting up and testing the Multi-Agent System Coordinator that intelligently routes between the General Purpose Agent (GPA) and Users Management Service (UMS) Agent.

**Time Estimate:** 2-3 hours for setup + testing  
**Complexity:** Expert Level (⭐⭐⭐⭐⭐+)

---

## 🚀 Prerequisites

- ✅ Docker Desktop running
- ✅ DIAL API Key from EPAM
- ✅ EPAM VPN connected  
- ✅ WSL2 with Ubuntu
- ✅ Python 3.11+
- ✅ **Environment Variable:** `DIAL_API_KEY` set

---

## 📦 System Architecture

**Services to be Running:**
1. **DIAL Core** (8080) - API Gateway
2. **DIAL Chat** (3000) - UI
3. **Redis** (6379) - Cache
4. **Redis Insight** (6380) - Redis viewer
5. **Adapter DIAL** - Model adapter
6. **User Service** (8040) - Mock users (1000 users)
7. **UMS MCP Server** (8041) - User management tools
8. **UMS Agent** (8042) - User management agent
9. **Python Interpreter MCP** (8050) - Code execution
10. **DuckDuckGo Search MCP** (8051) - Web search
11. **General Purpose Agent** (8052) - GPA
12. **MAS Coordinator** (8055) - **YOUR APP**

---

## 🛠️ Complete Setup Steps

### Step 1: Set Environment Variable

```bash
# Set DIAL API KEY (replace with your actual key)
export DIAL_API_KEY="your_dial_api_key_here"

# Verify
echo $DIAL_API_KEY
```

**⚠️ Important:** Without this, UMS Agent and GPA won't work!

---

### Step 2: Navigate to Project

```bash
cd /mnt/c/Users/AndreyPopov/ai-dial-mas-coordinator-for-gpa-uma
```

---

### Step 3: Update Configuration

**Edit `core/config.json` and replace `{YOUR_DIAL_API_KEY}`:**

```bash
# Open config file
nano core/config.json

# Find and replace all occurrences of {YOUR_DIAL_API_KEY}
# with your actual DIAL API key

# Or use sed (replace YOUR_KEY with actual key)
sed -i 's/{YOUR_DIAL_API_KEY}/YOUR_KEY/g' core/config.json
```

---

### Step 4: Start All Docker Services

```bash
# Start all 11 services
docker compose up -d

# Wait for services to initialize (important!)
sleep 30

# Verify all services are running
docker compose ps
```

**Expected Output:**
```
NAME                              STATUS
chat                              Up
core                              Up
redis                             Up
redis-insight                     Up
adapter-dial                      Up
userservice                       Up
ums-mcp-server                    Up
ums-agent                         Up
python-interpreter-mcp-server     Up
ddg-search-mcp-server            Up
general-purpose-agent             Up
```

**Troubleshooting:**

If any service is not running:
```bash
# View logs for specific service
docker compose logs userservice
docker compose logs ums-agent
docker compose logs general-purpose-agent

# Restart specific service
docker compose restart userservice
```

---

### Step 5: Verify Services

**Test 1: Check User Service**
```bash
curl http://localhost:8040/users | jq '.[0]'
```
Expected: User object with id, name, email, etc.

**Test 2: Check UMS MCP Server**
```bash
curl http://localhost:8041/health
```
Expected: `{"status": "healthy"}`

**Test 3: Check GPA**
```bash
curl -X POST http://localhost:8052/openai/deployments/general-purpose-agent/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hi"}]}'
```
Expected: JSON response with assistant message

**Test 4: Check DIAL Core**
```bash
curl http://localhost:8080
```
Expected: HTML response or JSON with API info

---

### Step 6: Set Up MAS Coordinator Application

```bash
# Create virtual environment
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Expected Dependencies:**
- `aidial-sdk` - DIAL application framework
- `aidial-client` - DIAL API client
- `httpx` - Async HTTP client
- `pydantic` - Data validation

---

### Step 7: Start MAS Coordinator

```bash
# Run the coordinator (in a new terminal or background)
python -m task.app

# Or run in background
nohup python -m task.app > coordinator.log 2>&1 &

# Check logs
tail -f coordinator.log
```

**Expected Output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8055
```

---

## 🧪 Testing the MAS Coordinator

### Test Phase 1: Verify Configuration

**Open Browser:** http://localhost:3000

**Expected:** DIAL Chat UI loads

**Check Marketplace:**
1. Click on "Marketplace" or application selector
2. Verify these applications are available:
   - ✅ MAS Coordinator Agent
   - ✅ General Purpose Agent
   - ✅ GPT 4o model
   - ✅ DALL-E model

**If not visible:**
```bash
# Restart DIAL Core
docker compose restart core

# Wait 10 seconds
sleep 10

# Refresh browser
```

---

### Test Phase 2: UMS Agent Routing

**Select:** MAS Coordinator Agent from marketplace

**Test Case 1: User Search**

```
User: Do we have Andrej Karpathy as a user?

Expected Behavior:
1. Stage: "Coordination Request"
   └─ {"agent_name": "UMS", "additional_instructions": null}
   
2. Stage: "Call UMS Agent"
   ├─ "Created new UMS conversation: ums-conv-456"
   └─ [UMS searches users]
   
3. Final Response:
   "No, Andrej Karpathy is not currently in our system."

✅ CORRECT: Routed to UMS, conversation created, search performed
❌ WRONG: Routed to GPA, or error
```

**Test Case 2: Add User**

```
User: Add Andrej Karpathy as a user to our system

Expected Behavior:
1. Stage: "Coordination Request"
   └─ {"agent_name": "UMS", ...}
   
2. Stage: "Call UMS Agent"
   └─ [Reuses previous UMS conversation]
   └─ [UMS creates user]
   
3. Final Response:
   "User Andrej Karpathy has been successfully added to the system."

✅ CORRECT: Reused UMS conversation, user created
❌ WRONG: Created new conversation (should reuse)
```

**Test Case 3: Verify User Added**

```
User: Do we have Andrej Karpathy now?

Expected Behavior:
1. Routes to UMS again
2. Finds Andrej Karpathy in system
3. Response: "Yes, Andrej Karpathy is now in our system."

✅ CORRECT: User management conversation continues
```

---

### Test Phase 3: GPA Routing

**Start NEW Conversation** (important for testing routing)

**Test Case 4: Weather Search**

```
User: What's the weather in Kyiv?

Expected Behavior:
1. Stage: "Coordination Request"
   └─ {"agent_name": "GPA", ...}
   
2. Stage: "Call GPA Agent"
   ├─ Substage: "Web Search" (from GPA)
   │  └─ "Searching for Kyiv weather..."
   ├─ GPA Response: "Temperature 15°C, cloudy"
   
3. Final Response:
   "The current weather in Kyiv is 15°C with cloudy skies."

✅ CORRECT: Routed to GPA, web search performed, stages propagated
❌ WRONG: Routed to UMS, or stages not visible
```

**Test Case 5: Image Generation**

```
User: Generate a picture of Kyiv weather

Expected Behavior:
1. Routes to GPA
2. Stage: "Call GPA Agent"
   ├─ Substage: "Image Generation"
   │  └─ "Generating image..."
   ├─ Attachment: Image appears
3. Final Response + Image visible

✅ CORRECT: Image generated and displayed
❌ WRONG: No image, or error
```

---

### Test Phase 4: Mixed Conversation

**Test Case 6: Switch Between Agents**

```
Message 1: "Do we have user John?"
  → Should route to UMS
  → UMS searches, finds John Doe

Message 2: "What's the weather?"
  → Should route to GPA
  → GPA asks for location

Message 3: "In Paris"
  → Should route to GPA (continue GPA conversation)
  → GPA provides Paris weather

Message 4: "Add user Alice"
  → Should route to UMS (reuse UMS conversation)
  → UMS creates Alice

✅ CORRECT: Each agent maintains separate conversation
❌ WRONG: Agents get confused by other agent's messages
```

---

### Test Phase 5: File Attachments (GPA)

**Test Case 7: CSV Analysis**

```
1. Attach tests/report.csv file
2. User: "Generate a bar chart from this data"

Expected Behavior:
1. Routes to GPA
2. Stage: "Call GPA Agent"
   ├─ Substage: "File Content Extraction"
   ├─ Substage: "Python Code Interpreter"
   │  └─ "Executing code to generate chart..."
   ├─ Attachment: Chart image
3. Final Response + Chart visible

✅ CORRECT: File processed, chart generated
```

---

## 🔍 Debugging & Verification

### Check Coordinator Logs

```bash
# View coordinator logs
tail -f coordinator.log

# Look for:
- "coordination_request: {...}"
- "Agent response: {...}"
- "Final response: {...}"
```

### Check UMS Agent Logs

```bash
docker compose logs -f ums-agent

# Look for:
- Conversation creation
- MCP tool calls
- User searches
```

### Check GPA Logs

```bash
docker compose logs -f general-purpose-agent

# Look for:
- Tool calls (web_search, python_interpreter)
- Stage operations
- File processing
```

### Check Redis (Conversations)

**Open Redis Insight:** http://localhost:6380

1. Click "Add Database"
2. Connection:
   - Host: `redis` (not localhost!)
   - Port: `6379`
3. Browse keys:
   - UMS conversations: `conversation:*`
   - DIAL cache: `dial:*`

---

## 🐛 Common Issues & Solutions

### Issue 1: Services Not Starting

**Symptoms:**
```
docker compose ps shows some services as "Exited"
```

**Solution:**
```bash
# Check which service failed
docker compose ps -a

# View logs for failed service
docker compose logs userservice

# Common fix: Restart service
docker compose restart userservice

# Or restart all
docker compose down
docker compose up -d
```

---

### Issue 2: DIAL API Key Error

**Symptoms:**
```
Error: Unauthorized (401)
UMS Agent logs: "DIAL_API_KEY not set"
```

**Solution:**
```bash
# Set environment variable
export DIAL_API_KEY="your_key"

# Restart services that need it
docker compose restart ums-agent
docker compose restart general-purpose-agent

# Update core/config.json
nano core/config.json
# Replace {YOUR_DIAL_API_KEY} with actual key

# Restart core
docker compose restart core
```

---

### Issue 3: MAS Coordinator Not in Marketplace

**Symptoms:**
- Only GPA and GPT-4o visible
- MAS Coordinator missing

**Solution:**
```bash
# 1. Check core/config.json
cat core/config.json | jq '.applications'
# Should show "mas-coordinator"

# 2. Restart core
docker compose restart core
sleep 10

# 3. Clear browser cache
# Ctrl+Shift+R in browser

# 4. Check coordinator is running
curl http://localhost:8055/health || echo "Not running"

# If not running:
python -m task.app
```

---

### Issue 4: Stages Not Propagating from GPA

**Symptoms:**
- GPA response appears but no substages
- Just flat text output

**Solution:**
```bash
# Check gpa.py implementation
grep "stages_map" task/coordination/gpa.py

# Verify stage processing in logs
tail -f coordinator.log | grep -i stage

# Test GPA directly
curl -X POST http://localhost:8052/openai/deployments/general-purpose-agent/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Search weather"}], "stream": true}'
```

---

### Issue 5: UMS Conversation Not Persisting

**Symptoms:**
- Every UMS call creates new conversation
- UMS forgets previous messages

**Solution:**
```bash
# Check state management in ums_agent.py
grep "_UMS_CONVERSATION_ID" task/coordination/ums_agent.py

# Verify Redis is working
docker compose exec redis redis-cli PING
# Should respond: PONG

# Check if state is being set
# Add debug logging:
# logger.info(f"UMS conv ID: {ums_conversation_id}")
```

---

## 📊 Service URLs Reference

| Service | URL | Purpose |
|---------|-----|---------|
| **DIAL Chat** | http://localhost:3000 | User interface |
| **DIAL Core** | http://localhost:8080 | API gateway |
| **Redis Insight** | http://localhost:6380 | Redis viewer |
| **User Service** | http://localhost:8040 | Mock users |
| **UMS MCP** | http://localhost:8041 | User tools |
| **UMS Agent** | http://localhost:8042 | User management |
| **Python MCP** | http://localhost:8050 | Code execution |
| **DuckDuckGo MCP** | http://localhost:8051 | Web search |
| **GPA** | http://localhost:8052 | General agent |
| **MAS Coordinator** | http://localhost:8055 | **YOUR APP** |

---

## ✅ Testing Checklist

### Configuration ✅
- [ ] `DIAL_API_KEY` environment variable set
- [ ] `core/config.json` updated with API keys
- [ ] All 12 applications/models in config
- [ ] MAS Coordinator listed in applications

### Services ✅
- [ ] Docker: 11 services running
- [ ] User Service: 1000 users generated
- [ ] UMS MCP: Health check passes
- [ ] UMS Agent: Responds to requests
- [ ] GPA: Responds to requests
- [ ] MAS Coordinator: Running on 8055

### Routing ✅
- [ ] UMS queries route to UMS Agent
- [ ] GPA queries route to GPA
- [ ] Coordination decision visible in stage
- [ ] Additional instructions passed when needed

### UMS Features ✅
- [ ] UMS conversation created on first call
- [ ] Conversation ID persisted in state
- [ ] Subsequent calls reuse conversation
- [ ] User search works
- [ ] User creation works

### GPA Features ✅
- [ ] Web search works
- [ ] Image generation works
- [ ] Python interpreter works
- [ ] File processing works
- [ ] Stages propagated to coordinator
- [ ] Attachments propagated

### Mixed Conversations ✅
- [ ] Can switch between UMS and GPA
- [ ] Each agent maintains separate history
- [ ] State management works correctly
- [ ] No context contamination

---

## 🚀 Advanced Testing

### Test Scenario 1: Complex User Query

```
1. "Find all users in engineering department"
   → UMS: Searches by department filter
   
2. "Send them an email about the meeting"
   → Should route to GPA (email is not user management)
   → GPA: Might say "I can't send emails, but here's a draft"
   
3. "Actually, just show me their emails"
   → UMS: Retrieves email list from search results
```

### Test Scenario 2: Data Analysis Workflow

```
1. Attach report.csv
2. "Analyze this sales data"
   → GPA: Extracts file, uses Python interpreter
   
3. "Who are the top sales people in our system?"
   → Routes to UMS (user search)
   → Returns user list
   
4. "Create a chart comparing their performance"
   → Routes to GPA (chart generation)
   → Uses Python interpreter with data
```

---

## 📝 Performance Benchmarks

**Expected Latencies:**

```
Coordination Request: ~500ms
  └─ LLM structured output

UMS Agent Call: ~1-3s
  └─ Conversation management + MCP tool execution

GPA Call: ~2-30s
  └─ Depends on tools used (web search, code execution, etc.)

Final Response: ~500ms
  └─ LLM synthesis

Total: 4-35s (mostly agent execution time)
```

**Optimization Opportunities:**

1. **Parallel Coordination:**
```python
# Instead of sequential
response = await coordinate_then_call_then_finalize()

# Consider pipeline
coordinate_task = asyncio.create_task(coordinate())
# Start agent call as soon as decision ready
```

2. **Caching:**
```python
# Cache coordination decisions
if query_similar_to_previous:
    reuse_agent_decision()
```

---

## 🎯 Success Criteria

### ✅ Implementation Complete When:

1. **All services running:**
   - 11 Docker containers healthy
   - MAS Coordinator application running

2. **Configuration correct:**
   - API keys set
   - All applications visible in marketplace

3. **Routing works:**
   - UMS queries → UMS Agent
   - GPA queries → GPA
   - Decisions visible in stages

4. **Features propagate:**
   - GPA stages appear in coordinator
   - GPA attachments visible
   - UMS conversation persists

5. **Test cases pass:**
   - All 7 test cases successful
   - Mixed conversations work correctly

---

## 🎓 What You've Built

A production-quality Multi-Agent System Coordinator featuring:

1. **Intelligent Routing:** LLM-based agent selection
2. **Context Management:** Per-agent conversation filtering
3. **Feature Propagation:** Stages, attachments, state
4. **Stateful Agents:** UMS conversation persistence
5. **Transparent Operation:** User sees all coordination decisions

**Result:** A **sophisticated MAS** that seamlessly routes between specialized agents! 🎉

---

## 📚 Next Steps

### Extend the System:

1. **Add More Agents:**
   - Email Agent
   - Calendar Agent
   - Analytics Agent

2. **Advanced Routing:**
   - Multi-agent queries (call GPA + UMS)
   - Agent fallback strategies
   - Load balancing between agent replicas

3. **Enhanced Coordination:**
   - Learn from past decisions
   - Cache common routing patterns
   - A/B test coordination prompts

4. **Production Features:**
   - Health checks
   - Circuit breakers
   - Distributed tracing
   - Metrics and monitoring

**Estimated Time:** 4-8 hours per enhancement

You've completed the most complex task in the series! 🚀🎊

