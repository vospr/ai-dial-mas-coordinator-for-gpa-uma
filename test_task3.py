"""
Test script for Task 3: MAS Coordinator with routing to UMS Agent

This script tests:
1. Coordinator routing to UMS Agent
2. Message history preservation
3. Final response generation

Prerequisites:
- DIAL Core running on http://localhost:8080
- UMS Agent running on http://localhost:8042
- MAS Coordinator running on http://localhost:8055
"""

import asyncio
import json
import os
from typing import Dict, Any

import httpx


DIAL_ENDPOINT = os.getenv('DIAL_ENDPOINT', 'http://localhost:8080')
MAS_COORDINATOR_ENDPOINT = os.getenv('MAS_COORDINATOR_ENDPOINT', 'http://localhost:8055')
UMS_AGENT_ENDPOINT = os.getenv('UMS_AGENT_ENDPOINT', 'http://localhost:8042')
DIAL_API_KEY = os.getenv('DIAL_API_KEY', 'dial_api_key')


class TestResult:
    """Test result container"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.details = {}

    def __str__(self):
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        result = f"{status}: {self.name}"
        if self.error:
            result += f"\n   Error: {self.error}"
        if self.details:
            result += f"\n   Details: {json.dumps(self.details, indent=2)}"
        return result


async def test_coordinator_routing_to_ums() -> TestResult:
    """Test 1: Verify coordinator routes to UMS Agent for user management queries"""
    result = TestResult("Coordinator routes to UMS Agent")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Test query that should route to UMS Agent
            response = await client.post(
                f"{MAS_COORDINATOR_ENDPOINT}/openai/deployments/mas-coordinator/chat/completions",
                headers={
                    "Authorization": f"Bearer {DIAL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": "Do we have Andrej Karpathy as a user?"
                        }
                    ],
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                result.error = f"HTTP {response.status_code}: {response.text}"
                return result
            
            data = response.json()
            result.details["response_status"] = response.status_code
            result.details["has_choices"] = "choices" in data and len(data["choices"]) > 0
            
            if result.details["has_choices"]:
                choice = data["choices"][0]
                message = choice.get("message", {})
                result.details["has_content"] = "content" in message and len(message["content"]) > 0
                
                # Check for stages indicating coordination
                stages = choice.get("stages", [])
                coordination_found = any(
                    "Coordination Request" in stage.get("name", "") or 
                    "UMS" in stage.get("name", "") 
                    for stage in stages
                )
                result.details["has_coordination_stages"] = coordination_found
                
                if result.details["has_content"] and coordination_found:
                    result.passed = True
            
    except httpx.ConnectError as e:
        result.error = f"Connection error: {str(e)}. Is MAS Coordinator running on {MAS_COORDINATOR_ENDPOINT}?"
    except Exception as e:
        result.error = f"Unexpected error: {str(e)}"
    
    return result


async def test_message_history_preservation() -> TestResult:
    """Test 2: Verify message history is preserved across requests"""
    result = TestResult("Message history preservation")
    
    try:
        conversation_id = f"test-conv-{os.urandom(4).hex()}"
        messages_history = []
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # First message
            messages_history.append({
                "role": "user",
                "content": "Do we have Andrej Karpathy as a user?"
            })
            
            response1 = await client.post(
                f"{MAS_COORDINATOR_ENDPOINT}/openai/deployments/mas-coordinator/chat/completions",
                headers={
                    "Authorization": f"Bearer {DIAL_API_KEY}",
                    "Content-Type": "application/json",
                    "x-conversation-id": conversation_id
                },
                json={
                    "messages": messages_history.copy(),
                    "stream": False
                }
            )
            
            if response1.status_code != 200:
                result.error = f"First request failed: HTTP {response1.status_code}"
                return result
            
            data1 = response1.json()
            if "choices" in data1 and len(data1["choices"]) > 0:
                assistant_msg = data1["choices"][0].get("message", {})
                messages_history.append({
                    "role": "assistant",
                    "content": assistant_msg.get("content", "")
                })
            
            # Second message in same conversation
            messages_history.append({
                "role": "user",
                "content": "Add Andrej Karpathy as a user to our system"
            })
            
            response2 = await client.post(
                f"{MAS_COORDINATOR_ENDPOINT}/openai/deployments/mas-coordinator/chat/completions",
                headers={
                    "Authorization": f"Bearer {DIAL_API_KEY}",
                    "Content-Type": "application/json",
                    "x-conversation-id": conversation_id
                },
                json={
                    "messages": messages_history.copy(),
                    "stream": False
                }
            )
            
            if response2.status_code != 200:
                result.error = f"Second request failed: HTTP {response2.status_code}"
                return result
            
            data2 = response2.json()
            result.details["conversation_id"] = conversation_id
            result.details["first_request_success"] = response1.status_code == 200
            result.details["second_request_success"] = response2.status_code == 200
            result.details["messages_in_second_request"] = len(messages_history)
            
            # Check if UMS conversation ID is preserved in state
            if "choices" in data2 and len(data2["choices"]) > 0:
                choice = data2["choices"][0]
                state = choice.get("message", {}).get("custom_content", {}).get("state", {})
                result.details["has_state"] = bool(state)
                result.details["has_ums_conversation_id"] = "ums_conversation_id" in state
                
                if result.details["has_ums_conversation_id"]:
                    result.passed = True
                else:
                    result.error = "UMS conversation ID not found in state"
            
    except Exception as e:
        result.error = f"Unexpected error: {str(e)}"
    
    return result


async def test_final_response_generation() -> TestResult:
    """Test 3: Verify final response is generated based on UMS Agent response"""
    result = TestResult("Final response generation")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{MAS_COORDINATOR_ENDPOINT}/openai/deployments/mas-coordinator/chat/completions",
                headers={
                    "Authorization": f"Bearer {DIAL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": "Add Andrej Karpathy as a user to our system"
                        }
                    ],
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                result.error = f"HTTP {response.status_code}: {response.text}"
                return result
            
            data = response.json()
            result.details["response_status"] = response.status_code
            
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                message = choice.get("message", {})
                content = message.get("content", "")
                
                result.details["has_content"] = bool(content)
                result.details["content_length"] = len(content)
                
                # Check for stages showing the flow
                stages = choice.get("stages", [])
                stage_names = [stage.get("name", "") for stage in stages]
                result.details["stages"] = stage_names
                
                has_coordination = any("Coordination Request" in name for name in stage_names)
                has_agent_call = any("Call" in name and "Agent" in name for name in stage_names)
                
                result.details["has_coordination_stage"] = has_coordination
                result.details["has_agent_call_stage"] = has_agent_call
                
                if content and has_coordination and has_agent_call:
                    result.passed = True
                else:
                    result.error = f"Missing required components. Content: {bool(content)}, Coordination: {has_coordination}, Agent Call: {has_agent_call}"
            
    except Exception as e:
        result.error = f"Unexpected error: {str(e)}"
    
    return result


async def test_ums_agent_connectivity() -> TestResult:
    """Test 4: Verify UMS Agent is accessible"""
    result = TestResult("UMS Agent connectivity")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to create a conversation to verify UMS Agent is running
            response = await client.post(
                f"{UMS_AGENT_ENDPOINT}/conversations",
                json={"title": "Test Conversation"},
                timeout=10.0
            )
            
            result.details["status_code"] = response.status_code
            if response.status_code == 200:
                data = response.json()
                result.details["conversation_id"] = data.get("id")
                result.passed = True
            else:
                result.error = f"UMS Agent returned HTTP {response.status_code}"
            
    except httpx.ConnectError:
        result.error = f"Cannot connect to UMS Agent at {UMS_AGENT_ENDPOINT}. Is it running?"
    except Exception as e:
        result.error = f"Unexpected error: {str(e)}"
    
    return result


async def run_all_tests():
    """Run all test scenarios"""
    print("=" * 70)
    print("Task 3: MAS Coordinator Test Suite")
    print("=" * 70)
    print()
    
    print(f"Configuration:")
    print(f"  - DIAL Endpoint: {DIAL_ENDPOINT}")
    print(f"  - MAS Coordinator: {MAS_COORDINATOR_ENDPOINT}")
    print(f"  - UMS Agent: {UMS_AGENT_ENDPOINT}")
    print()
    
    tests = [
        ("UMS Agent Connectivity", test_ums_agent_connectivity),
        ("Coordinator Routing", test_coordinator_routing_to_ums),
        ("Message History Preservation", test_message_history_preservation),
        ("Final Response Generation", test_final_response_generation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Running: {test_name}...")
        result = await test_func()
        results.append(result)
        print(result)
        print()
    
    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print()
    
    for result in results:
        status = "✅" if result.passed else "❌"
        print(f"{status} {result.name}")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())

