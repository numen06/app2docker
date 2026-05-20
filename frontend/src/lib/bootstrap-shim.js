/**
 * Maps ES imports `from 'bootstrap'` to the global loaded via CDN (see index.html).
 * Keeps legacy App.vue JS API working without the npm bootstrap package.
 */

function getBootstrap() {
  return typeof window !== 'undefined' ? window.bootstrap : undefined
}

function noopDropdownInstance() {
  return {
    toggle() {},
    show() {},
    hide() {},
    dispose() {},
    update() {},
  }
}

function noopModalInstance() {
  return {
    show() {},
    hide() {},
    toggle() {},
    dispose() {},
    handleUpdate() {},
  }
}

function noopToastInstance() {
  return {
    show() {},
    hide() {},
    dispose() {},
  }
}

export class Dropdown {
  static getInstance(element) {
    const D = getBootstrap()?.Dropdown
    return D?.getInstance?.(element) ?? null
  }

  static getOrCreateInstance(element, options) {
    const D = getBootstrap()?.Dropdown
    if (D?.getOrCreateInstance) {
      return D.getOrCreateInstance(element, options)
    }
    return noopDropdownInstance()
  }
}

export class Modal {
  static getInstance(element) {
    const M = getBootstrap()?.Modal
    return M?.getInstance?.(element) ?? null
  }

  static getOrCreateInstance(element, options) {
    const M = getBootstrap()?.Modal
    if (M?.getOrCreateInstance) {
      return M.getOrCreateInstance(element, options)
    }
    return noopModalInstance()
  }
}

export class Toast {
  static getInstance(element) {
    const T = getBootstrap()?.Toast
    return T?.getInstance?.(element) ?? null
  }

  static getOrCreateInstance(element, options) {
    const T = getBootstrap()?.Toast
    if (T?.getOrCreateInstance) {
      return T.getOrCreateInstance(element, options)
    }
    return noopToastInstance()
  }
}
