import { spawnSync, spawn } from 'node:child_process'
import { createServer } from 'node:net'
import { lstatSync, mkdirSync, realpathSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = spawnSync('git', ['-C', appRoot, 'rev-parse', '--show-toplevel'], { encoding: 'utf8' })
const branch = spawnSync('git', ['-C', appRoot, 'branch', '--show-current'], { encoding: 'utf8' })

if (repositoryRoot.status !== 0 || branch.status !== 0) {
  throw new Error('Cannot confirm the Breeding Next source checkout.')
}

const projectRoot = realpathSync(repositoryRoot.stdout.trim())
if (!projectRoot.includes(`${path.sep}easylab-next${path.sep}modules${path.sep}breeding`) || branch.stdout.trim() !== 'codex/easylab-next-20261113') {
  throw new Error(`Refusing to launch from outside the EasyLab Next Breeding checkout: ${projectRoot}`)
}
if (!process.env.EASYLAB_PYTHON) {
  throw new Error('Set EASYLAB_PYTHON to the Breeding Next Python environment before starting the API.')
}

const runtimeRoot = path.resolve(projectRoot, '../../runtime')
const moduleRuntime = path.join(runtimeRoot, 'breeding')
const writablePaths = {
  data: path.join(moduleRuntime, 'data'),
  settings: path.join(moduleRuntime, 'settings'),
  exports: path.join(moduleRuntime, 'exports'),
  userData: path.join(moduleRuntime, 'user-data'),
  pythonCache: path.join(moduleRuntime, 'python-cache'),
}

function assertNoSymlinkComponents(target) {
  const absolute = path.resolve(target)
  let current = path.parse(absolute).root
  for (const part of absolute.slice(current.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, part)
    try {
      if (lstatSync(current).isSymbolicLink()) throw new Error(`Refusing a linked runtime path: ${current}`)
    } catch (error) {
      if (error.code !== 'ENOENT') throw error
      break
    }
  }
}

for (const directory of Object.values(writablePaths)) {
  assertNoSymlinkComponents(directory)
  mkdirSync(directory, { recursive: true })
}

const api = createServer()
await new Promise((resolve, reject) => {
  api.once('error', (error) => reject(new Error(`Breeding API port 18522 is unavailable: ${error.message}`)))
  api.listen(18522, '127.0.0.1', () => api.close(resolve))
})

const child = spawn(process.env.EASYLAB_PYTHON, [
  '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '18522',
], {
  cwd: appRoot,
  stdio: 'inherit',
  env: {
    ...process.env,
    EASYLAB_RUNTIME_ROOT: runtimeRoot,
    EASYLAB_DATA_PATH: writablePaths.data,
    EASYLAB_SETTINGS_PATH: writablePaths.settings,
    EASYLAB_EXPORTS_PATH: writablePaths.exports,
    EASYLAB_USER_DATA_DIR: writablePaths.userData,
    PYTHONDONTWRITEBYTECODE: '1',
    PYTHONPYCACHEPREFIX: writablePaths.pythonCache,
  },
})

child.once('error', (error) => {
  console.error(`Could not start the Breeding API: ${error.message}`)
  process.exitCode = 1
})
child.once('exit', (code, signal) => {
  process.exitCode = code ?? (signal ? 1 : 0)
})

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.once(signal, () => child.kill(signal))
}
