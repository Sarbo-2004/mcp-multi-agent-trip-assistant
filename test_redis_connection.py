from memory.redis_trip_memory import RedisTripMemory

store = RedisTripMemory()

session_id = store.create_session_id()

memory = store.default_memory()
memory["request_memory"]["source"] = "West Bengal"
memory["request_memory"]["destination"] = "Odisha"
memory["request_memory"]["days"] = 4
memory["request_memory"]["travelers"] = 5

store.save(session_id, memory)

loaded = store.load(session_id)

print("SESSION:", session_id)
print("LOADED REQUEST MEMORY:", loaded["request_memory"])