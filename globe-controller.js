/**
 * PRAVAH — Ultra-Realistic Cinematic 3D Web-GIS Globe Controller
 * Powered by Three.js & Globe.gl with holographic command-center HUD
 */

(function () {
  // 20 Central Water Commission & IndoFloods Western Ghats gauge stations with flood probabilities
  const WESTERN_GHATS_STATIONS = [
    {
      station_id: 'MH_GAK_12',
      name: 'Karad',
      river: 'Krishna',
      district: 'Satara',
      lat: 17.2944,
      lng: 74.1903,
      rainfall: '85.0 mm',
      warning_level_m: 563.0,
      danger_level_m: 565.8,
      risk: 'EMERGENCY',
      flood_prob: 0.84, // 84%
      color: '#ef4444',
    },
    {
      station_id: 'MH_GAK_17',
      name: 'Mahad',
      river: 'Savitri',
      district: 'Raigad',
      lat: 18.0833,
      lng: 73.4167,
      rainfall: '94.2 mm',
      warning_level_m: 6.5,
      danger_level_m: 8.0,
      risk: 'EMERGENCY',
      flood_prob: 0.92, // 92%
      color: '#ef4444',
    },
    {
      station_id: 'MH_GAK_01',
      name: 'Terwad',
      river: 'Panchganga',
      district: 'Kolhapur',
      lat: 16.7333,
      lng: 74.5833,
      rainfall: '62.4 mm',
      warning_level_m: 535.0,
      danger_level_m: 537.5,
      risk: 'WARNING',
      flood_prob: 0.65, // 65%
      color: '#f97316',
    },
    {
      station_id: 'MH_GAK_18',
      name: 'Badlapur',
      river: 'Ulhas',
      district: 'Thane',
      lat: 19.1500,
      lng: 73.2667,
      rainfall: '58.0 mm',
      warning_level_m: 16.5,
      danger_level_m: 18.2,
      risk: 'WARNING',
      flood_prob: 0.58, // 58%
      color: '#f97316',
    },
    {
      station_id: 'MH_GAK_14',
      name: 'Chiplun',
      river: 'Vashishti',
      district: 'Ratnagiri',
      lat: 17.5333,
      lng: 73.5167,
      rainfall: '68.0 mm',
      warning_level_m: 6.8,
      danger_level_m: 8.2,
      risk: 'WARNING',
      flood_prob: 0.62, // 62%
      color: '#f97316',
    },
    {
      station_id: 'MH_GAK_03',
      name: 'Kurundwad',
      river: 'Krishna',
      district: 'Kolhapur',
      lat: 16.6833,
      lng: 74.6000,
      rainfall: '36.5 mm',
      warning_level_m: 532.0,
      danger_level_m: 534.5,
      risk: 'ADVISORY',
      flood_prob: 0.38, // 38%
      color: '#eab308',
    },
    {
      station_id: 'MH_GAK_02',
      name: 'Shirol',
      river: 'Dudhganga',
      district: 'Kolhapur',
      lat: 16.7167,
      lng: 74.6167,
      rainfall: '34.0 mm',
      warning_level_m: 533.0,
      danger_level_m: 535.5,
      risk: 'ADVISORY',
      flood_prob: 0.35, // 35%
      color: '#eab308',
    },
    {
      station_id: 'MH_GAK_16',
      name: 'Poladpur',
      river: 'Savitri',
      district: 'Raigad',
      lat: 17.9833,
      lng: 73.4667,
      rainfall: '32.0 mm',
      warning_level_m: 14.0,
      danger_level_m: 16.0,
      risk: 'ADVISORY',
      flood_prob: 0.32, // 32%
      color: '#eab308',
    },
    {
      station_id: 'MH_GAK_08',
      name: 'Bhilawadi',
      river: 'Krishna',
      district: 'Sangli',
      lat: 17.0167,
      lng: 74.4500,
      rainfall: '28.0 mm',
      warning_level_m: 542.0,
      danger_level_m: 544.5,
      risk: 'ADVISORY',
      flood_prob: 0.28, // 28%
      color: '#eab308',
    },
    {
      station_id: 'MH_GAK_09',
      name: 'Sangli Bridge',
      river: 'Krishna',
      district: 'Sangli',
      lat: 16.8500,
      lng: 74.5667,
      rainfall: '18.2 mm',
      warning_level_m: 540.0,
      danger_level_m: 542.5,
      risk: 'NORMAL',
      flood_prob: 0.18, // 18%
      color: '#06b6d4',
    },
    {
      station_id: 'MH_GAK_04',
      name: 'Arjunwad',
      river: 'Krishna',
      district: 'Kolhapur',
      lat: 16.6333,
      lng: 74.6500,
      rainfall: '16.0 mm',
      warning_level_m: 530.0,
      danger_level_m: 532.5,
      risk: 'NORMAL',
      flood_prob: 0.15,
      color: '#06b6d4',
    },
    {
      station_id: 'MH_GAK_05',
      name: 'Rajaapur',
      river: 'Krishna',
      district: 'Kolhapur',
      lat: 16.5833,
      lng: 74.7000,
      rainfall: '14.5 mm',
      warning_level_m: 528.0,
      danger_level_m: 530.5,
      risk: 'NORMAL',
      flood_prob: 0.12,
      color: '#06b6d4',
    },
    {
      station_id: 'MH_GAK_06',
      name: 'Koyna Dam',
      river: 'Koyna',
      district: 'Satara',
      lat: 17.4000,
      lng: 73.7500,
      rainfall: '45.0 mm',
      warning_level_m: 657.0,
      danger_level_m: 660.0,
      risk: 'NORMAL',
      flood_prob: 0.22,
      color: '#06b6d4',
    },
    {
      station_id: 'MH_GAK_07',
      name: 'Warna Dam',
      river: 'Warna',
      district: 'Sangli',
      lat: 17.1333,
      lng: 73.8000,
      rainfall: '38.0 mm',
      warning_level_m: 624.0,
      danger_level_m: 627.0,
      risk: 'NORMAL',
      flood_prob: 0.20,
      color: '#06b6d4',
    },
    {
      station_id: 'MH_GAK_10',
      name: 'Miraj',
      river: 'Krishna',
      district: 'Sangli',
      lat: 16.8333,
      lng: 74.6333,
      rainfall: '15.0 mm',
      warning_level_m: 538.0,
      danger_level_m: 540.5,
      risk: 'NORMAL',
      flood_prob: 0.14,
      color: '#06b6d4',
    },
    {
      station_id: 'MH_GAK_11',
      name: 'Shirala',
      river: 'Morna',
      district: 'Sangli',
      lat: 16.9833,
      lng: 74.1333,
      rainfall: '21.0 mm',
      warning_level_m: 575.0,
      danger_level_m: 577.5,
      risk: 'NORMAL',
      flood_prob: 0.16,
      color: '#06b6d4',
    },
    {
      station_id: 'MH_GAK_13',
      name: 'Patan',
      river: 'Kera',
      district: 'Satara',
      lat: 17.3667,
      lng: 73.9000,
      rainfall: '22.4 mm',
      warning_level_m: 580.0,
      danger_level_m: 582.5,
      risk: 'NORMAL',
      flood_prob: 0.17,
      color: '#06b6d4',
    },
    {
      station_id: 'MH_GAK_15',
      name: 'Khed',
      river: 'Jagbudi',
      district: 'Ratnagiri',
      lat: 17.7167,
      lng: 73.3833,
      rainfall: '17.5 mm',
      warning_level_m: 6.0,
      danger_level_m: 7.5,
      risk: 'NORMAL',
      flood_prob: 0.15,
      color: '#06b6d4',
    },
    {
      station_id: 'MH_GAK_19',
      name: 'Bhivpuri',
      river: 'Pej',
      district: 'Raigad',
      lat: 18.9333,
      lng: 73.3333,
      rainfall: '19.0 mm',
      warning_level_m: 24.0,
      danger_level_m: 26.5,
      risk: 'NORMAL',
      flood_prob: 0.16,
      color: '#06b6d4',
    },
    {
      station_id: 'MH_GAK_20',
      name: 'Khopoli',
      river: 'Patalganga',
      district: 'Raigad',
      lat: 18.7833,
      lng: 73.3500,
      rainfall: '23.0 mm',
      warning_level_m: 48.0,
      danger_level_m: 50.5,
      risk: 'NORMAL',
      flood_prob: 0.19,
      color: '#06b6d4',
    },
  ];

  let globeInstance = null;
  let idleTimer = null;
  let isInteracting = false;
  let cloudsMesh = null;

  // Western Ghats regional target coordinate
  const WESTERN_GHATS_VIEW = {
    lat: 18.2,
    lng: 73.9,
    altitude: 0.72,
  };

  // Cinematic start perspective (deep space view of Earth against stars)
  const GLOBAL_SPACE_VIEW = {
    lat: 20.0,
    lng: 55.0,
    altitude: 3.2,
  };

  /**
   * Initializes the Ultra-Realistic Cinematic 3D Globe
   */
  function initGlobe() {
    const container = document.getElementById('globeViewport');
    const loader = document.getElementById('globeLoader');
    const tooltip = document.getElementById('globeTooltip');

    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 540;

    // Check if Globe.gl and Three.js libraries are ready
    if (typeof Globe === 'undefined' || typeof THREE === 'undefined') {
      console.warn('[PRAVAH Globe] WebGL libraries loading dynamically...');
      loadGlobeLibraries(() => initGlobe());
      return;
    }

    try {
      // 1. Initialize Globe Instance with NASA Blue Marble & Topographical Bump Map (Requirement 1 & 2)
      globeInstance = Globe()(container)
        .width(width)
        .height(height)
        .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg') // High-res satellite image
        .bumpImageUrl('https://unpkg.com/three-globe/example/img/earth-topology.png') // Topographical relief depth
        .backgroundImageUrl('https://unpkg.com/three-globe/example/img/night-sky.png') // High-res starfield space background
        .atmosphereColor('#06b6d4') // Theme Neon Cyan atmospheric glow
        .atmosphereAltitude(0.26)
        .showAtmosphere(true);

      // 2. Add Transparent Independently Rotating Cloud Layer (Requirement 2)
      const globeRadius = globeInstance.getGlobeRadius();
      const cloudsTextureUrl = 'https://unpkg.com/three-globe/example/img/earth-clouds.png';
      new THREE.TextureLoader().load(cloudsTextureUrl, (cloudsTexture) => {
        cloudsMesh = new THREE.Mesh(
          new THREE.SphereGeometry(globeRadius * 1.015, 75, 75),
          new THREE.MeshPhongMaterial({
            map: cloudsTexture,
            transparent: true,
            opacity: 0.38,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
          })
        );
        globeInstance.scene().add(cloudsMesh);

        // Continuous independent cloud rotation
        (function animateClouds() {
          if (cloudsMesh) {
            cloudsMesh.rotation.y += -0.0006;
          }
          requestAnimationFrame(animateClouds);
        })();
      });

      // 3. Add Advanced 3D Glowing Data Pillars Protruding from Surface (Requirement 3)
      globeInstance
        .customLayerData(WESTERN_GHATS_STATIONS)
        .customThreeObject((d) => {
          // Dynamic pillar height based on Flood Probability percentage (Requirement 3)
          const prob = d.flood_prob || 0.2;
          const height = Math.max(6, prob * 36); // 3D height proportional to flood probability
          const radius = 1.3;

          // Hexagonal 3D Column Geometry
          const geometry = new THREE.CylinderGeometry(radius * 0.75, radius, height, 8);
          geometry.translate(0, height / 2, 0); // Base sits exactly on the surface

          const isEmergency = d.risk === 'EMERGENCY';
          const isWarning = d.risk === 'WARNING';
          const isAdvisory = d.risk === 'ADVISORY';

          const colorHex = isEmergency ? 0xef4444 : isWarning ? 0xf97316 : isAdvisory ? 0xeab308 : 0x06b6d4;

          const material = new THREE.MeshPhongMaterial({
            color: colorHex,
            emissive: colorHex,
            emissiveIntensity: isEmergency ? 0.95 : 0.45,
            transparent: true,
            opacity: 0.92,
            shininess: 100,
          });

          const pillar = new THREE.Mesh(geometry, material);

          // Top Beacon Cap (glowing sphere beacon at pillar apex)
          const beaconGeo = new THREE.SphereGeometry(radius * 1.25, 12, 12);
          const beaconMat = new THREE.MeshBasicMaterial({
            color: isEmergency ? 0xffffff : colorHex,
            transparent: true,
            opacity: 0.95,
          });
          const beacon = new THREE.Mesh(beaconGeo, beaconMat);
          beacon.position.set(0, height, 0);
          pillar.add(beacon);

          // Base footprint telemetry ring
          const ringGeo = new THREE.RingGeometry(radius * 0.8, radius * 2.2, 16);
          ringGeo.rotateX(-Math.PI / 2);
          const ringMat = new THREE.MeshBasicMaterial({
            color: colorHex,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.65,
          });
          const baseRing = new THREE.Mesh(ringGeo, ringMat);
          pillar.add(baseRing);

          pillar.userData = {
            station: d,
            baseHeight: height,
            baseEmissive: isEmergency ? 0.95 : 0.45,
          };

          return pillar;
        })
        .customThreeObjectUpdate((obj, d) => {
          // Map coordinates & orient perpendicular to globe surface
          const coords = globeInstance.getCoords(d.lat, d.lng, 0.005);
          obj.position.copy(coords);
          // Vector from globe center (0,0,0) to position is the radial surface normal
          obj.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), obj.position.clone().normalize());
        })
        // 4. Raycasting / Hover: Glowing 3D Pillar & Glass Tooltip (Requirement 4)
        .onCustomLayerHover((obj, prevObj) => {
          if (prevObj && prevObj.material) {
            prevObj.scale.set(1, 1, 1);
            prevObj.material.emissiveIntensity = prevObj.userData.baseEmissive;
          }
          if (obj && obj.material) {
            obj.scale.set(1.25, 1.25, 1.25);
            obj.material.emissiveIntensity = 1.45; // Make 3D pillar glow brighter
            handlePointHover(obj.userData.station, tooltip);
          } else if (!obj) {
            handlePointHover(null, tooltip);
          }
        })
        .onCustomLayerClick((obj) => {
          if (!obj || !obj.userData) return;
          const station = obj.userData.station;
          globeInstance.pointOfView(
            {
              lat: station.lat,
              lng: station.lng,
              altitude: 0.42,
            },
            1400
          );
          if (window.PRAVAH && window.PRAVAH.selectStation) {
            window.PRAVAH.selectStation(station.station_id);
          }
        });

      // 5. Rippling Wave Animation Radiating Outward (Requirement 3)
      globeInstance
        .ringsData(WESTERN_GHATS_STATIONS)
        .ringLat('lat')
        .ringLng('lng')
        .ringColor((d) =>
          d.risk === 'EMERGENCY'
            ? (t) => `rgba(239, 68, 68, ${0.9 * (1 - t)})`
            : d.risk === 'WARNING'
            ? (t) => `rgba(249, 115, 22, ${0.75 * (1 - t)})`
            : (t) => `rgba(6, 182, 212, ${0.55 * (1 - t)})`
        )
        .ringMaxRadius((d) => (d.risk === 'EMERGENCY' ? 4.8 : d.risk === 'WARNING' ? 3.0 : 1.8))
        .ringPropagationSpeed((d) => (d.risk === 'EMERGENCY' ? 4.2 : 2.0))
        .ringRepeatPeriod((d) => (d.risk === 'EMERGENCY' ? 600 : 1300));

      // 6. Cinematic Start: Zoomed Out in Space (Requirement 4)
      globeInstance.pointOfView(GLOBAL_SPACE_VIEW, 0);

      // 7. Idle Spin & Camera Controls (Requirement 4)
      const controls = globeInstance.controls();
      controls.autoRotate = true;
      controls.autoRotateSpeed = 0.6;
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;

      controls.addEventListener('start', () => {
        isInteracting = true;
        controls.autoRotate = false;
        clearTimeout(idleTimer);
      });

      controls.addEventListener('end', () => {
        clearTimeout(idleTimer);
        idleTimer = setTimeout(() => {
          isInteracting = false;
          controls.autoRotate = true;
        }, 3500);
      });

      // 8. Cinematic Camera Fly-In: Zeroing in on Western Ghats of India (Requirement 4)
      setTimeout(() => {
        globeInstance.pointOfView(WESTERN_GHATS_VIEW, 3200);
      }, 1200);

      // 9. Hide Radar Skeleton Loader
      if (loader) {
        loader.style.opacity = '0';
        setTimeout(() => {
          loader.style.display = 'none';
        }, 400);
      }

      // 10. Bind Navigation Controls
      bindMapControls();
      window.addEventListener('resize', handleResize);

      console.log('[PRAVAH] Ultra-Realistic Cinematic 3D Globe Initialized.');
    } catch (err) {
      console.error('[PRAVAH Globe Error]', err);
      if (loader) {
        loader.innerHTML = `
          <div style="color: #ef4444; font-family: monospace; text-align: center; padding: 2rem;">
            <p>Holographic 3D Globe Render Error</p>
            <small style="color: #94a3b8;">${err.message}</small>
          </div>
        `;
      }
    }
  }

  /**
   * Tooltip Handler for 3D Marker Hover
   */
  function handlePointHover(point, tooltip) {
    if (!tooltip) return;

    if (!point) {
      tooltip.style.display = 'none';
      return;
    }

    const idEl = document.getElementById('tooltipStationId');
    const badgeEl = document.getElementById('tooltipRiskBadge');
    const nameEl = document.getElementById('tooltipStationName');
    const basinEl = document.getElementById('tooltipRiverBasin');
    const rainEl = document.getElementById('tooltipRainfall');
    const warnEl = document.getElementById('tooltipWarning');

    if (idEl) idEl.textContent = point.station_id;
    if (nameEl) nameEl.textContent = `${point.name} Catchment`;
    if (basinEl) basinEl.textContent = `${point.river} Basin • ${point.district}`;
    if (rainEl) rainEl.textContent = point.rainfall;
    if (warnEl) warnEl.textContent = `${point.warning_level_m} m`;

    if (badgeEl) {
      const pct = Math.round((point.flood_prob || 0.2) * 100);
      badgeEl.textContent = `${point.risk} (${pct}%)`;
      badgeEl.className = `tooltip-risk-pill ${point.risk.toLowerCase()}`;
    }

    tooltip.style.display = 'block';
  }

  /**
   * Bind Map Control Buttons
   */
  function bindMapControls() {
    const zoomInBtn = document.getElementById('globeZoomInBtn');
    const zoomOutBtn = document.getElementById('globeZoomOutBtn');
    const resetBtn = document.getElementById('globeResetGhatsBtn');

    if (zoomInBtn) {
      zoomInBtn.addEventListener('click', () => {
        if (!globeInstance) return;
        const pov = globeInstance.pointOfView();
        globeInstance.pointOfView({ ...pov, altitude: Math.max(0.18, pov.altitude - 0.35) }, 600);
      });
    }

    if (zoomOutBtn) {
      zoomOutBtn.addEventListener('click', () => {
        if (!globeInstance) return;
        const pov = globeInstance.pointOfView();
        globeInstance.pointOfView({ ...pov, altitude: Math.min(3.8, pov.altitude + 0.45) }, 600);
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        if (!globeInstance) return;
        globeInstance.pointOfView(WESTERN_GHATS_VIEW, 1600);
      });
    }
  }

  function handleResize() {
    const container = document.getElementById('globeViewport');
    if (!container || !globeInstance) return;
    globeInstance.width(container.clientWidth).height(container.clientHeight);
  }

  function loadGlobeLibraries(onReady) {
    if (typeof THREE === 'undefined') {
      const threeScript = document.createElement('script');
      threeScript.src = 'https://unpkg.com/three@0.160.0/build/three.min.js';
      threeScript.onload = () => loadGlobeScript(onReady);
      document.head.appendChild(threeScript);
    } else {
      loadGlobeScript(onReady);
    }
  }

  function loadGlobeScript(onReady) {
    const globeScript = document.createElement('script');
    globeScript.src = 'https://unpkg.com/globe.gl@2.32.0/dist/globe.gl.min.js';
    globeScript.onload = () => {
      if (onReady) onReady();
    };
    document.head.appendChild(globeScript);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGlobe);
  } else {
    initGlobe();
  }

  window.PRAVAH_GLOBE = {
    resetToWesternGhats: () => globeInstance && globeInstance.pointOfView(WESTERN_GHATS_VIEW, 1500),
    zoomToGlobal: () => globeInstance && globeInstance.pointOfView(GLOBAL_SPACE_VIEW, 1500),
    flyToStation: (stationId) => {
      if (!globeInstance) return;
      const st = WESTERN_GHATS_STATIONS.find((s) => s.station_id === stationId);
      if (st) {
        globeInstance.pointOfView(
          {
            lat: st.lat,
            lng: st.lng,
            altitude: 0.42,
          },
          1400
        );
      }
    },
    getStations: () => WESTERN_GHATS_STATIONS,
  };
})();
