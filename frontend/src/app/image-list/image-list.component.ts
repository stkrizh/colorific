import { Component, Input, OnChanges, OnInit, SimpleChange } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { ActivatedRoute } from "@angular/router";
import { StateService } from "../state.service";


interface Image {
  id: string
  details_url: string
  regular_url: string;
  small_url: string;
  has_colors: boolean;
}


interface ImageListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Array<Image>
}


@Component({
  selector: "app-image-list",
  templateUrl: "./image-list.component.html",
  styleUrls: ["./image-list.component.scss"]
})
export class ImageListComponent implements OnInit, OnChanges {
  @Input() rgb: string | null;

  count: number = 0;
  next_url: string | null = null;
  previous_url: string | null = null;
  images: Array<Image> = [];

  constructor(
    private http: HttpClient,
    private route: ActivatedRoute,
    private state: StateService
  ) {}

  ngOnInit() {
    this.route.paramMap.subscribe(params => {
      let routerRGB = params.get("rgb");
      if (routerRGB !== null) {
        this.rgb = routerRGB;
        this.fetchImages();
      }
    })
  }

  ngOnChanges(changes: {[propKey: string]: SimpleChange}) {
    if ("rgb" in changes)
      this.fetchImages();
  }

  fetchImages() {
    this.state.showLoaderOverlay();
    const url = `http://localhost:8000/images?rgb=${this.rgb}`;
    this.http.get(url).subscribe(
      (response) => {
        this.state.turnOffLoaderOverlay();
        const imagesResponse = <ImageListResponse>response;
        this.images = imagesResponse.results;
        this.count = imagesResponse.count;
        this.next_url = imagesResponse.next;
        this.previous_url = imagesResponse.previous;
      },
      (error) => {
        this.state.turnOffLoaderOverlay();
        console.log(error);
      }
    );
  }

  showImageDetail(imageID: string) {
    this.state.showImageDetail(imageID);
  }
}
