import fastify from 'fastify'
import jwt, { UserType } from '@fastify/jwt'
import crypto from 'crypto'
import app from './app'
import users from './users'

const server = fastify()

server.get('/', app)

const { publicKey, privateKey } = crypto.generateKeyPairSync("rsa", {
  modulusLength: 2048,
  publicKeyEncoding: { type: "spki", format: "pem" },
  privateKeyEncoding: { type: "pkcs8", format: "pem" },
})

server.register(jwt, {
  // secret: 'secretkey', // HS256
  secret: { private: privateKey, public: publicKey },
  sign: { algorithm: 'RS256' },
  formatUser: (payload: any) => userService.find(payload.sub) as UserType
})

server.addHook('onRequest', async (request) => {
  if (request.raw.url && ['/signup', '/signin'].includes(request.raw.url)) {
    return
  }
  await request.jwtVerify()
})

const userService = new users.UserService()

server.post<{ Body: { name: string, email: string } }>('/signup', async (request, replay) => {
  const { name, email } = request.body
  const user = userService.create(name, email)

  if (!user) return { message: 'user already' }

  const token = await replay.jwtSign({ iss: 'inoh.com', sub: user.id }, { expiresIn: '10s' })
  return { token }
})
server.post<{ Body: { name: string } }>('/signin', async (request, replay) => {
  const user = userService.findByName(request.body.name)

  if (!user) return { message: 'user not found' }

  const token = await replay.jwtSign({ iss: 'inoh.com', sub: user.id }, { expiresIn: '10s' })
  return { token }
})
server.get('/me', (request) => request.user)

server.listen({ port: 5000, host: '0.0.0.0' }, (err, address) => {
  if (err) {
    server.log.error(err)
    process.exit(1)
  }
  server.log.info(`server listening on ${address}`)
})
