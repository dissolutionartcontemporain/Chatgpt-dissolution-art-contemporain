import cv2
import numpy as np
import os
import shutil
from tkinter import filedialog, Tk, Label, Button, Entry, messagebox, colorchooser, Checkbutton, IntVar, Toplevel, StringVar
from tkinter import ttk
from PIL import Image, ImageTk
import random

# Globals
img_path = None
output_folder = "output_frames"

def charger_image():
    global img_path
    img_path = filedialog.askopenfilename(
        title="Choisir une image",
        filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.gif")]
    )
    if img_path:
        image = Image.open(img_path)
        image.thumbnail((400, 400))
        photo = ImageTk.PhotoImage(image)
        label_image.config(image=photo)
        label_image.image = photo

def choisir_couleur():
    couleur = colorchooser.askcolor(initialcolor='#FFFFFF')
    if couleur[0] is not None:
        rgb = tuple(int(c) for c in couleur[0])
        color_entry.delete(0, 'end')
        color_entry.insert(0, f"{rgb[0]},{rgb[1]},{rgb[2]}")

def effacer_pixels():
    global img_path

    if not img_path:
        messagebox.showwarning("Erreur", "Aucune image chargée.")
        return

    try:
        color_str = color_entry.get()
        color_to_remove = tuple(map(int, color_str.split(',')))
        if len(color_to_remove) != 3 or any(c < 0 or c > 255 for c in color_to_remove):
            raise ValueError("La couleur doit être 3 entiers entre 0 et 255.")
        pixels_per_step = int(pixels_entry.get())
        if pixels_per_step <= 0:
            raise ValueError("Pixels par étape doit être > 0.")
        mode = "aléatoire" if mode_var.get() == 1 else "ordonné"
        fps = int(fps_entry.get())
        if fps <= 0:
            raise ValueError("FPS doit être > 0.")
        first_copies = int(first_copies_entry.get())
        last_copies = int(last_copies_entry.get())
        if first_copies < 0 or last_copies < 0:
            raise ValueError("Le nombre de copies doit être >= 0.")
    except Exception as e:
        messagebox.showerror("Erreur", f"Paramètres invalides : {e}")
        return

    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)

    img = cv2.imread(img_path)
    mask = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(mask, 240, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    points_to_remove = []
    for contour in contours:
        mask_temp = np.zeros(mask.shape, dtype=np.uint8)
        cv2.drawContours(mask_temp, [contour], -1, 255, thickness=cv2.FILLED)
        ys, xs = np.where(mask_temp == 255)
        points_to_remove.extend(zip(xs, ys))

    if mode == "aléatoire":
        random.shuffle(points_to_remove)

    # Progress bar window for dissolution
    progress_win = Toplevel(root)
    progress_win.title("Progression")
    progress_label_var = StringVar()
    progress_label_var.set("Dissolution en cours...")
    Label(progress_win, textvariable=progress_label_var).pack(padx=10, pady=10)
    progress = ttk.Progressbar(progress_win, orient='horizontal', length=300, mode='determinate')
    progress.pack(padx=10, pady=10)
    progress["maximum"] = len(points_to_remove)

    img_copy = img.copy()
    steps = []

    # Copier la première image (non modifiée) plusieurs fois au début
    for c in range(first_copies):
        copy_path = os.path.join(output_folder, f"step_{c:04d}.png")
        cv2.imwrite(copy_path, img)
        steps.append(copy_path)

    # Dissolution progressive
    for i in range(0, len(points_to_remove), pixels_per_step):
        batch = points_to_remove[i:i + pixels_per_step]
        for (x, y) in batch:
            if 0 <= y < img_copy.shape[0] and 0 <= x < img_copy.shape[1]:
                img_copy[y, x] = color_to_remove
        step_path = os.path.join(output_folder, f"step_{i // pixels_per_step + first_copies:04d}.png")
        cv2.imwrite(step_path, img_copy)
        steps.append(step_path)
        progress["value"] = i
        progress_label_var.set(f"Dissolution : étape {i // pixels_per_step + 1} sur {len(points_to_remove) // pixels_per_step + 1}")
        progress_win.update()

    # Copier la dernière image plusieurs fois à la fin
    for c in range(last_copies):
        copy_path = os.path.join(output_folder, f"step_{len(steps) + c:04d}.png")
        cv2.imwrite(copy_path, img_copy)
        steps.append(copy_path)

    progress_win.destroy()
    messagebox.showinfo("Terminé", f"Dissolution terminée en {len(steps)} étapes.")
    creer_video(steps, fps)

    # Vidéo inversée si demandé
    if reverse_var.get() == 1:
        steps_inverted = list(reversed(steps))
        creer_video(steps_inverted, fps, "dissolution_video_inverse.mp4")

def creer_video(steps, fps, video_filename="dissolution_video.mp4"):
    if not steps:
        messagebox.showerror("Erreur", "Aucune étape enregistrée, impossible de créer la vidéo.")
        return

    frame = cv2.imread(steps[0])
    height, width, _ = frame.shape
    out = cv2.VideoWriter(video_filename, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    # Progress bar for video creation
    progress_video_win = Toplevel(root)
    progress_video_win.title("Création Vidéo")
    video_progress_label_var = StringVar()
    video_progress_label_var.set(f"Création de la vidéo '{video_filename}' en cours...")
    Label(progress_video_win, textvariable=video_progress_label_var).pack(padx=10, pady=10)
    progress_video = ttk.Progressbar(progress_video_win, orient='horizontal', length=300, mode='determinate')
    progress_video.pack(padx=10, pady=10)
    progress_video["maximum"] = len(steps)

    for idx, img_path in enumerate(steps):
        frame = cv2.imread(img_path)
        out.write(frame)
        progress_video["value"] = idx + 1
        video_progress_label_var.set(f"Vidéo '{video_filename}' : image {idx + 1} sur {len(steps)}")
        progress_video_win.update()

    out.release()
    progress_video_win.destroy()
    messagebox.showinfo("Vidéo créée", f"Vidéo générée : {video_filename}")

root = Tk()
root.title("Dissolution d'Images faite avec ChatGPT")

messagebox.showinfo("Attention",
    "Pour de meilleures performances, veuillez choisir une image pas trop grande (idéalement moins de 1000x1000 pixels).")

label_image = Label(root)
label_image.pack()

Button(root, text="Charger Image", command=charger_image).pack()

Label(root, text="Couleur d'effacement (R,G,B) :").pack()
color_entry = Entry(root)
color_entry.insert(0, "255,255,255")
color_entry.pack()

Button(root, text="Choisir Couleur", command=choisir_couleur).pack()

Label(root, text="Pixels à effacer par étape :").pack()
pixels_entry = Entry(root)
pixels_entry.insert(0, "50")
pixels_entry.pack()

Label(root, text="FPS (images par seconde) pour la vidéo :").pack()
fps_entry = Entry(root)
fps_entry.insert(0, "30")
fps_entry.pack()

Label(root, text="Copies de la première image :").pack()
first_copies_entry = Entry(root)
first_copies_entry.insert(0, "30")
first_copies_entry.pack()

Label(root, text="Copies de la dernière image :").pack()
last_copies_entry = Entry(root)
last_copies_entry.insert(0, "30")
last_copies_entry.pack()

mode_var = IntVar(value=0)
mode_checkbox = Checkbutton(root, text="Mode aléatoire (sinon ordonné)", variable=mode_var)
mode_checkbox.pack()

reverse_var = IntVar(value=0)
reverse_checkbox = Checkbutton(root, text="Générer vidéo inversée", variable=reverse_var)
reverse_checkbox.pack()

Button(root, text="Lancer la Dissolution", command=effacer_pixels).pack()

root.mainloop()
