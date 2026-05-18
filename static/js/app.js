document.addEventListener('DOMContentLoaded', () => {
  const seatButtons = document.querySelectorAll('.seat-map .seat:not(.booked)');
  const seatInput = document.getElementById('seat_no');
  const bookingForm = document.getElementById('booking-form');
  const formMessage = document.getElementById('form-message');

  seatButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      seatButtons.forEach((seat) => seat.classList.remove('selected'));
      btn.classList.add('selected');
      if (seatInput) seatInput.value = btn.dataset.seat;
    });
  });

  if (bookingForm) {
    bookingForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      formMessage.textContent = 'Submitting and mining blockchain transaction...';
      formMessage.className = 'form-message';

      const scheduleId = bookingForm.dataset.scheduleId;
      const formData = new FormData(bookingForm);

      try {
        const response = await fetch(`/book/${scheduleId}`, {
          method: 'POST',
          body: formData,
        });

        const result = await response.json();
        if (!response.ok || !result.success) {
          throw new Error(result.message || 'Booking failed');
        }

        formMessage.textContent = `${result.message} Block hash: ${result.block_hash.slice(0, 18)}...`;
        formMessage.classList.add('success');
        setTimeout(() => {
          window.location.href = result.redirect_url;
        }, 1200);
      } catch (error) {
        formMessage.textContent = error.message;
        formMessage.classList.add('error');
      }
    });
  }
});
