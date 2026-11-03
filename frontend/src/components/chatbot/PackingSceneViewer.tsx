import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import type { SceneData } from '../../types/workflow'

interface PackingSceneViewerProps {
  sceneData?: SceneData
  containerName?: string
  productMeshUrl?: string
  height?: string
}

export default function PackingSceneViewer({
  sceneData,
  containerName = 'Packaging Container',
  productMeshUrl,
  height = 'h-64 sm:h-72',
}: PackingSceneViewerProps) {
  const mountRef = useRef<HTMLDivElement>(null)
  const [wireframe, setWireframe] = useState(false)
  const [autoRotate, setAutoRotate] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [modelStatus, setModelStatus] = useState<'loading' | 'cad' | 'box_fallback'>('box_fallback')

  const controlsRef = useRef<OrbitControls | null>(null)
  const initialCamPos = useRef<THREE.Vector3>(new THREE.Vector3(0, 0, 0))
  const materialsRef = useRef<THREE.MeshStandardMaterial[]>([])

  const containerDims = sceneData?.container?.dimensions
  const items = sceneData?.items ?? []

  useEffect(() => {
    const container = mountRef.current
    if (!container || !containerDims) return
    let isSubscribed = true
    setModelStatus(productMeshUrl ? 'loading' : 'box_fallback')

    // 1. Scene setup
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf8fafc) // Slate-50 background

    // 2. Dimensions
    const cL = Number(containerDims.length) || 300
    const cW = Number(containerDims.width) || 200
    const cH = Number(containerDims.height) || 150

    const cCenterX = cL / 2
    const cCenterY = cW / 2
    const cCenterZ = cH / 2

    // 3. Camera setup
    const width = container.clientWidth || 400
    const heightPx = container.clientHeight || 260
    const camera = new THREE.PerspectiveCamera(40, width / heightPx, 1, 10000)

    // Set isometric camera position based on container bounding radius
    const maxDim = Math.max(cL, cW, cH)
    const camDist = maxDim * 2.2
    camera.position.set(camDist * 1.1, camDist * 1.0, camDist * 1.3)
    initialCamPos.current.copy(camera.position)

    // 4. Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setSize(width, heightPx)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap

    container.innerHTML = ''
    container.appendChild(renderer.domElement)

    // 5. Controls
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.target.set(0, 0, 0)
    controls.autoRotate = autoRotate
    controls.autoRotateSpeed = 1.5
    controlsRef.current = controls

    // 6. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.4)
    scene.add(ambientLight)

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.8)
    keyLight.position.set(maxDim * 2, maxDim * 3, maxDim * 2)
    keyLight.castShadow = true
    scene.add(keyLight)

    const fillLight = new THREE.DirectionalLight(0x94a3b8, 0.9)
    fillLight.position.set(-maxDim * 2, -maxDim, -maxDim * 2)
    scene.add(fillLight)

    // 7. Base Floor / Shadow Receiver
    const floorSize = maxDim * 2.5
    const floorGeo = new THREE.PlaneGeometry(floorSize, floorSize)
    const floorMat = new THREE.MeshBasicMaterial({
      color: 0xedf2f7,
      side: THREE.DoubleSide,
    })
    const floor = new THREE.Mesh(floorGeo, floorMat)
    floor.rotation.x = -Math.PI / 2
    floor.position.y = -cH / 2 - 0.5
    scene.add(floor)

    // Grid helper on floor
    const grid = new THREE.GridHelper(floorSize, 20, 0xcbd5e1, 0xe2e8f0)
    grid.position.y = -cH / 2
    scene.add(grid)

    // 8. Container Outer Box (Wireframe + Semi-transparent walls)
    const rootGroup = new THREE.Group()

    // Outer container geometry: (Length = X, Height = Y, Width = Z)
    const containerGeo = new THREE.BoxGeometry(cL, cH, cW)

    // Transparent container walls
    const containerMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.12,
      roughness: 0.4,
      metalness: 0.1,
      depthWrite: false,
    })
    const containerMesh = new THREE.Mesh(containerGeo, containerMat)
    rootGroup.add(containerMesh)

    // Crisp Container Edges
    const containerEdgesGeo = new THREE.EdgesGeometry(containerGeo)
    const containerEdgesMat = new THREE.LineBasicMaterial({
      color: 0x0284c7, // Sky-600
      linewidth: 2,
    })
    const containerEdges = new THREE.LineSegments(containerEdgesGeo, containerEdgesMat)
    rootGroup.add(containerEdges)

    // 9. Placed Items inside container
    materialsRef.current = []
    const fallbackItemsGroup = new THREE.Group()
    const cadItemsGroup = new THREE.Group()

    items.forEach((item) => {
      const itemDims = item.dimensions || { length: 50, width: 50, height: 50 }
      const itemL = Number(itemDims.length) || 50
      const itemW = Number(itemDims.width) || 50
      const itemH = Number(itemDims.height) || 50

      // Three.js geometry: (X = Length, Y = Height, Z = Width)
      const itemGeo = new THREE.BoxGeometry(itemL, itemH, itemW)

      const colorHex = item.color || '#0284c7'
      const itemMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(colorHex),
        roughness: 0.35,
        metalness: 0.25,
        wireframe,
      })
      materialsRef.current.push(itemMat)

      const itemMesh = new THREE.Mesh(itemGeo, itemMat)
      itemMesh.castShadow = true
      itemMesh.receiveShadow = true

      // Coordinates mapping:
      // Three.js X = packaging X - centerX
      // Three.js Y = packaging Z - centerZ (height is Y)
      // Three.js Z = packaging Y - centerY (width is Z)
      const posX = (item.position?.x ?? 0) - cCenterX
      const posY = (item.position?.z ?? 0) - cCenterZ
      const posZ = (item.position?.y ?? 0) - cCenterY

      itemMesh.position.set(posX, posY, posZ)
      fallbackItemsGroup.add(itemMesh)

      // Add crisp edges to item
      const itemEdgesGeo = new THREE.EdgesGeometry(itemGeo)
      const itemEdgesMat = new THREE.LineBasicMaterial({
        color: 0x0f172a,
        opacity: 0.45,
        transparent: true,
      })
      const itemEdges = new THREE.LineSegments(itemEdgesGeo, itemEdgesMat)
      itemEdges.position.copy(itemMesh.position)
      fallbackItemsGroup.add(itemEdges)
    })

    rootGroup.add(fallbackItemsGroup)
    rootGroup.add(cadItemsGroup)
    scene.add(rootGroup)

    if (productMeshUrl) {
      new GLTFLoader().load(
        productMeshUrl,
        (gltf) => {
          if (!isSubscribed) return

          const sourceBounds = new THREE.Box3().setFromObject(gltf.scene)
          const sourceSize = new THREE.Vector3()
          const sourceCenter = new THREE.Vector3()
          sourceBounds.getSize(sourceSize)
          sourceBounds.getCenter(sourceCenter)

          if (sourceSize.x <= 0 || sourceSize.y <= 0 || sourceSize.z <= 0) {
            setModelStatus('box_fallback')
            return
          }

          items.forEach((item) => {
            const itemDims = item.dimensions || { length: 50, width: 50, height: 50 }
            const itemL = Number(itemDims.length) || 50
            const itemW = Number(itemDims.width) || 50
            const itemH = Number(itemDims.height) || 50
            const itemGroup = new THREE.Group()
            itemGroup.position.set(
              (item.position?.x ?? 0) + itemL / 2 - cCenterX,
              (item.position?.z ?? 0) + itemH / 2 - cCenterZ,
              (item.position?.y ?? 0) + itemW / 2 - cCenterY,
            )

            const model = gltf.scene.clone(true)
            model.scale.set(itemL / sourceSize.x, itemH / sourceSize.y, itemW / sourceSize.z)
            model.position.set(
              -sourceCenter.x * model.scale.x,
              -sourceCenter.y * model.scale.y,
              -sourceCenter.z * model.scale.z,
            )
            model.traverse((object) => {
              if (object instanceof THREE.Mesh) {
                object.castShadow = true
                object.receiveShadow = true
              }
            })
            itemGroup.add(model)
            cadItemsGroup.add(itemGroup)
          })

          fallbackItemsGroup.visible = false
          setModelStatus('cad')
        },
        undefined,
        (error) => {
          if (!isSubscribed) return
          console.warn('Product CAD mesh unavailable; showing dimension-accurate boxes instead.', error)
          setModelStatus('box_fallback')
        },
      )
    }

    // 10. Animation Loop
    let animationFrameId: number

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // 11. Resize handling
    const handleResize = () => {
      if (!container) return
      const newW = container.clientWidth
      const newH = container.clientHeight
      camera.aspect = newW / newH
      camera.updateProjectionMatrix()
      renderer.setSize(newW, newH)
    }

    const resizeObserver = new ResizeObserver(() => handleResize())
    resizeObserver.observe(container)

    // Teardown
    return () => {
      isSubscribed = false
      cancelAnimationFrame(animationFrameId)
      resizeObserver.disconnect()
      controls.dispose()
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [containerDims, items, isExpanded, productMeshUrl])

  // Update wireframe mode dynamically
  useEffect(() => {
    materialsRef.current.forEach((mat) => {
      mat.wireframe = wireframe
    })
  }, [wireframe])

  // Update autoRotate mode dynamically
  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = autoRotate
    }
  }, [autoRotate])

  const handleResetCamera = () => {
    if (controlsRef.current && initialCamPos.current) {
      controlsRef.current.reset()
      controlsRef.current.autoRotate = autoRotate
    }
  }

  if (!containerDims) {
    return null
  }

  return (
    <div
      className={`relative w-full rounded-xl border border-slate-200 overflow-hidden bg-slate-50 shadow-2xs transition-all duration-200 ${
        isExpanded ? 'h-96 sm:h-[450px]' : height
      }`}
    >
      {/* 3D Canvas Mount Point */}
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Top Overlay Badge */}
      <div className="absolute top-2.5 left-2.5 flex items-center gap-2 pointer-events-none z-10">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold text-slate-700 bg-white/95 backdrop-blur-xs border border-slate-200/90 rounded-md shadow-2xs">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          {containerName} ({containerDims.length}×{containerDims.width}×{containerDims.height} mm)
        </span>
        <span className="hidden sm:inline-flex px-2 py-1 text-[11px] font-medium text-slate-500 bg-white/90 backdrop-blur-xs border border-slate-200/80 rounded-md shadow-2xs">
          {items.length} placed items
        </span>
        <span className="hidden sm:inline-flex px-2 py-1 text-[11px] font-medium text-slate-500 bg-white/90 backdrop-blur-xs border border-slate-200/80 rounded-md shadow-2xs">
          {modelStatus === 'loading' ? 'Loading product model…' : modelStatus === 'cad' ? 'CAD model' : 'Dimension box'}
        </span>
      </div>

      {/* Control Buttons Toolbar (Bottom Right) */}
      <div className="absolute bottom-2.5 right-2.5 flex items-center gap-1.5 z-10">
        {/* Auto Rotate Toggle */}
        <button
          type="button"
          onClick={() => setAutoRotate((prev) => !prev)}
          title={autoRotate ? 'Pause Rotation' : 'Auto Rotate'}
          className={`px-2 py-1 text-xs font-medium rounded-md border backdrop-blur-xs transition-colors cursor-pointer shadow-2xs ${
            autoRotate
              ? 'bg-sky-600 text-white border-sky-700'
              : 'bg-white/90 text-slate-700 border-slate-200 hover:bg-slate-100'
          }`}
        >
          {autoRotate ? 'Spinning' : 'Spin'}
        </button>

        {/* Wireframe Toggle */}
        <button
          type="button"
          onClick={() => setWireframe((prev) => !prev)}
          title={wireframe ? 'Solid Mode' : 'Wireframe Mode'}
          className={`px-2 py-1 text-xs font-medium rounded-md border backdrop-blur-xs transition-colors cursor-pointer shadow-2xs ${
            wireframe
              ? 'bg-sky-600 text-white border-sky-700'
              : 'bg-white/90 text-slate-700 border-slate-200 hover:bg-slate-100'
          }`}
        >
          Wire
        </button>

        {/* Reset View */}
        <button
          type="button"
          onClick={handleResetCamera}
          title="Reset Camera View"
          className="p-1.5 rounded-md bg-white/90 hover:bg-slate-100 text-slate-700 border border-slate-200 backdrop-blur-xs transition-colors cursor-pointer shadow-2xs"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
        </button>

        {/* Expand / Minimize Height */}
        <button
          type="button"
          onClick={() => setIsExpanded((prev) => !prev)}
          title={isExpanded ? 'Collapse View' : 'Expand View'}
          className="p-1.5 rounded-md bg-white/90 hover:bg-slate-100 text-slate-700 border border-slate-200 backdrop-blur-xs transition-colors cursor-pointer shadow-2xs"
        >
          {isExpanded ? (
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 9V4.5M9 9H4.5M9 9 3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5 5.25 5.25" />
            </svg>
          ) : (
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
            </svg>
          )}
        </button>
      </div>
    </div>
  )
}
