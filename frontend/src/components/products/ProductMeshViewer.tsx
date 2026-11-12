import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

interface ProductMeshViewerProps {
  productIdOrName?: string | number
  meshUrl?: string
  hasCadModel?: boolean
  className?: string
  height?: string
  autoRotateDefault?: boolean
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export default function ProductMeshViewer({
  productIdOrName,
  meshUrl,
  hasCadModel = false,
  className = '',
  height = 'h-64 sm:h-80',
  autoRotateDefault = true,
}: ProductMeshViewerProps) {
  const mountRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCadSource, setIsCadSource] = useState(hasCadModel)
  const [autoRotate, setAutoRotate] = useState(autoRotateDefault)
  const [wireframe, setWireframe] = useState(false)

  // References to control Three.js instance
  const controlsRef = useRef<OrbitControls | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const rootGroupRef = useRef<THREE.Group | null>(null)
  const initialCamPos = useRef<THREE.Vector3>(new THREE.Vector3(0, 0, 0))

  useEffect(() => {
    const container = mountRef.current
    if (!container) return

    setLoading(true)
    setError(null)

    // 1. Scene setup
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf8fafc) // Slate-50 solid
    sceneRef.current = scene

    // 2. Camera setup
    const width = container.clientWidth || 400
    const heightPx = container.clientHeight || 300
    const camera = new THREE.PerspectiveCamera(45, width / heightPx, 0.001, 5000)
    cameraRef.current = camera

    // 3. Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setSize(width, heightPx)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    container.innerHTML = ''
    container.appendChild(renderer.domElement)

    // 4. Lighting setup
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.2)
    scene.add(ambientLight)

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.8)
    dirLight1.position.set(500, 1000, 750)
    dirLight1.castShadow = true
    scene.add(dirLight1)

    const dirLight2 = new THREE.DirectionalLight(0x90b0d0, 0.8)
    dirLight2.position.set(-500, -500, -500)
    scene.add(dirLight2)

    // 5. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.autoRotate = autoRotate
    controls.autoRotateSpeed = 2.0
    controlsRef.current = controls

    // 6. Root group to hold mesh
    const rootGroup = new THREE.Group()
    scene.add(rootGroup)
    rootGroupRef.current = rootGroup

    // 7. Load GLB mesh generated/converted by Python trimesh
    const loader = new GLTFLoader()
    const targetMeshUrl =
      meshUrl || `${API_BASE}/products/${encodeURIComponent(productIdOrName || '')}/mesh`

    let isSubscribed = true

    loader.load(
      targetMeshUrl,
      (gltf) => {
        if (!isSubscribed) return
        const model = gltf.scene

        // Traverse model meshes and configure shadows and materials
        model.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.castShadow = true
            child.receiveShadow = true
            if (child.material) {
              if (Array.isArray(child.material)) {
                child.material.forEach((m) => {
                  m.roughness = 0.35
                  m.metalness = 0.25
                })
              } else {
                child.material.roughness = 0.35
                child.material.metalness = 0.25
              }
            }
          }
        })

        rootGroup.add(model)

        // Compute Bounding Box and center camera
        const bbox = new THREE.Box3().setFromObject(model)
        const size = new THREE.Vector3()
        bbox.getSize(size)
        const center = new THREE.Vector3()
        bbox.getCenter(center)

        // Center model at origin
        model.position.sub(center)

        // Compute optimal camera distance based on diagonal
        const maxDim = Math.max(size.x, size.y, size.z, 0.01)
        const fov = camera.fov * (Math.PI / 180)
        let cameraDist = maxDim / (2 * Math.tan(fov / 2))
        cameraDist *= 1.6 // Add comfortable margin

        camera.position.set(cameraDist * 0.8, cameraDist * 0.6, cameraDist)
        camera.lookAt(0, 0, 0)
        controls.target.set(0, 0, 0)
        controls.update()

        initialCamPos.current.copy(camera.position)

        // Add subtle ground shadow plane
        const shadowPlaneGeo = new THREE.PlaneGeometry(maxDim * 3, maxDim * 3)
        const shadowPlaneMat = new THREE.ShadowMaterial({ opacity: 0.15 })
        const shadowPlane = new THREE.Mesh(shadowPlaneGeo, shadowPlaneMat)
        shadowPlane.rotation.x = -Math.PI / 2
        shadowPlane.position.y = -size.y / 2
        shadowPlane.receiveShadow = true
        scene.add(shadowPlane)

        setLoading(false)
      },
      undefined,
      (err) => {
        if (!isSubscribed) return
        console.error('Failed to load 3D mesh via trimesh:', err)
        setError('Unable to load 3D mesh geometry from server.')
        setLoading(false)
      }
    )

    // Check custom headers via HEAD/GET if needed
    fetch(targetMeshUrl, { method: 'HEAD' })
      .then((res) => {
        const isCad = res.headers.get('X-Is-Cad-Model') === 'true'
        if (isSubscribed) setIsCadSource(isCad)
      })
      .catch(() => {})

    // 8. Animation loop
    let animId: number
    const animate = () => {
      animId = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // 9. Resize observer
    const handleResize = () => {
      if (!container) return
      const w = container.clientWidth
      const h = container.clientHeight
      if (w > 0 && h > 0) {
        camera.aspect = w / h
        camera.updateProjectionMatrix()
        renderer.setSize(w, h)
      }
    }

    const resizeObserver = new ResizeObserver(handleResize)
    resizeObserver.observe(container)

    // Cleanup
    return () => {
      isSubscribed = false
      cancelAnimationFrame(animId)
      resizeObserver.disconnect()
      controls.dispose()
      renderer.dispose()
      if (container) {
        container.innerHTML = ''
      }
    }
  }, [productIdOrName, meshUrl])

  // Sync autoRotate state with OrbitControls
  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = autoRotate
    }
  }, [autoRotate])

  // Sync wireframe toggle across materials
  useEffect(() => {
    if (!rootGroupRef.current) return
    rootGroupRef.current.traverse((child) => {
      if (child instanceof THREE.Mesh && child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach((m) => {
            m.wireframe = wireframe
          })
        } else {
          child.material.wireframe = wireframe
        }
      }
    })
  }, [wireframe])

  const handleResetCamera = () => {
    if (cameraRef.current && controlsRef.current) {
      cameraRef.current.position.copy(initialCamPos.current)
      controlsRef.current.target.set(0, 0, 0)
      controlsRef.current.update()
    }
  }

  return (
    <div
      className={`relative rounded-lg overflow-hidden border border-slate-200 bg-slate-50 flex flex-col ${height} ${className}`}
    >
      {/* 3D WebGL Canvas Mount */}
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Top Header Badge */}
      <div className="absolute top-2.5 left-2.5 z-10 flex items-center gap-1.5 select-none pointer-events-none">
        <span
          className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-md border shadow-2xs ${
            isCadSource
              ? 'bg-sky-600 text-white border-sky-700'
              : 'bg-white text-slate-700 border-slate-300'
          }`}
        >
          {isCadSource ? '3D CAD Geometry (.STEP)' : 'Trimesh 3D Geometry'}
        </span>
      </div>

      {/* Bottom Floating Control Toolbar */}
      {!loading && !error && (
        <div className="absolute bottom-2.5 right-2.5 z-10 flex items-center gap-1 bg-white/90 backdrop-blur-xs border border-slate-200 rounded-lg p-1 shadow-2xs select-none">
          {/* Auto-Rotate Toggle */}
          <button
            type="button"
            onClick={() => setAutoRotate((prev) => !prev)}
            title={autoRotate ? 'Pause auto-rotation' : 'Start auto-rotation'}
            className={`p-1.5 rounded text-xs font-medium transition cursor-pointer ${
              autoRotate ? 'bg-sky-100 text-sky-800' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
          </button>

          {/* Wireframe Mesh Toggle */}
          <button
            type="button"
            onClick={() => setWireframe((prev) => !prev)}
            title={wireframe ? 'Solid surface mode' : 'Wireframe mesh mode'}
            className={`p-1.5 rounded text-xs font-medium transition cursor-pointer ${
              wireframe ? 'bg-sky-100 text-sky-800' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" />
            </svg>
          </button>

          {/* Reset View Button */}
          <button
            type="button"
            onClick={handleResetCamera}
            title="Reset 3D camera view"
            className="p-1.5 rounded text-xs font-medium text-slate-600 hover:bg-slate-100 transition cursor-pointer"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 9l6 6m0-6l-6 6m12-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
          </button>
        </div>
      )}

      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 bg-slate-50/80 backdrop-blur-2xs flex flex-col items-center justify-center text-sky-700 z-20">
          <svg className="w-8 h-8 animate-spin mb-2 stroke-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          <span className="text-xs font-medium text-slate-600">Generating 3D mesh with trimesh...</span>
        </div>
      )}

      {/* Error Overlay */}
      {error && (
        <div className="absolute inset-0 bg-slate-50 flex flex-col items-center justify-center p-4 text-center z-20">
          <svg className="w-8 h-8 stroke-red-500 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
          <span className="text-xs text-slate-700 font-medium">{error}</span>
        </div>
      )}

      {/* Instruction Tip */}
      <div className="absolute bottom-2.5 left-2.5 z-10 text-[10px] text-slate-400 select-none pointer-events-none hidden sm:block">
        Left-click: Rotate &bull; Right-click: Pan &bull; Scroll: Zoom
      </div>
    </div>
  )
}
