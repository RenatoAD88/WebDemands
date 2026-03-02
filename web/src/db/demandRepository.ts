import { openDB } from 'idb'
import type { Demand } from '../types/demand'

const DB_NAME = 'webdemands-db'
const STORE = 'demands'

async function db() {
  return openDB(DB_NAME, 1, {
    upgrade(database) {
      if (!database.objectStoreNames.contains(STORE)) {
        database.createObjectStore(STORE, { keyPath: 'id' })
      }
    }
  })
}

export async function listDemands(): Promise<Demand[]> {
  return (await db()).getAll(STORE)
}

export async function saveDemand(demand: Demand): Promise<void> {
  await (await db()).put(STORE, demand)
}

export async function deleteDemand(id: string): Promise<void> {
  await (await db()).delete(STORE, id)
}

export async function exportDemands(): Promise<string> {
  const rows = await listDemands()
  return JSON.stringify(rows, null, 2)
}

export async function importDemands(raw: string): Promise<number> {
  const parsed = JSON.parse(raw) as Demand[]
  const database = await db()
  const tx = database.transaction(STORE, 'readwrite')
  for (const demand of parsed) {
    await tx.store.put(demand)
  }
  await tx.done
  return parsed.length
}
