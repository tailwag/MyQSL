const imageModal = document.getElementById('imageModal')
const modalImage = document.getElementById('modalImage')

imageModal.addEventListener('show.bs.modal', event => {
    const link = event.relatedTarget
    modalImage.src = link.getAttribute('href')
})
