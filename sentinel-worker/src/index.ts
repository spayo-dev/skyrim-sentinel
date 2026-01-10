import { Hono } from 'hono'
import { cors } from 'hono/cors'

type Bindings = {
  SENTINEL_HASHES: KVNamespace
}

const app = new Hono<{ Bindings: Bindings }>()

// Middleware
app.use('/*', cors())

// Routes
app.get('/', (c) => c.text('Skyrim Sentinel API is running.'))

app.get('/health', (c) => c.json({ status: 'ok', timestamp: new Date().toISOString() }))

app.post('/api/v1/scan', async (c) => {
  try {
    const body = await c.req.json()
    // TODO: Implement KV lookup logic here
    return c.json({ 
      message: "Scan received", 
      received: body,
      note: "KV lookup not yet implemented" 
    })
  } catch (e) {
    return c.json({ error: 'Invalid JSON' }, 400)
  }
})

export default app

