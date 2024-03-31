import fastify from 'fastify'
import app from './app'

const server = fastify()

server.get('/', app)

server.listen({ port: 5000, host: '0.0.0.0' }, (err, address) => {
  if (err) {
    server.log.error(err)
    process.exit(1)
  }
  server.log.info(`server listening on ${address}`)
})
